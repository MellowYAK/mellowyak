from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


class DurableJournal:
    def __init__(self, path: Path, payload: dict[str, Any]) -> None:
        self.path = path
        self.payload = payload

    @classmethod
    def create(cls, path: Path, payload: dict[str, Any]) -> DurableJournal:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.exists() or path.is_symlink():
            raise RuntimeError("APPLY_JOURNAL_ALREADY_EXISTS")
        journal = cls(path, {**payload, "events": []})
        journal.flush()
        return journal

    @classmethod
    def load(cls, path: Path) -> DurableJournal:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("APPLY_JOURNAL_INVALID")
        return cls(path, json.loads(path.read_text(encoding="utf-8")))

    def append(self, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "sequence": len(self.payload["events"]) + 1,
            "event_type": event_type,
            "details": details or {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.payload["events"].append(event)
        self.payload["state"] = event_type
        self.flush()
        return event

    def flush(self) -> None:
        content = (
            json.dumps(self.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        ).encode()
        descriptor, name = tempfile.mkstemp(prefix=".apply-journal-", dir=self.path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            self.path.chmod(0o600)
            fsync_directory(self.path.parent)
        finally:
            temporary.unlink(missing_ok=True)
