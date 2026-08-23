from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


class RedactingJsonFormatter(logging.Formatter):
    def __init__(self, secrets: tuple[str, ...], sensitive_paths: tuple[Path, ...]) -> None:
        super().__init__()
        self._secrets = tuple(item for item in secrets if item)
        self._paths = tuple(str(path) for path in sensitive_paths)

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        for secret in self._secrets:
            message = message.replace(secret, "[REDACTED]")
        for path in self._paths:
            message = message.replace(path, "[LOCAL_DATA_ROOT]")
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def configure_logging(log_dir: Path, session_token: str, data_root: Path) -> logging.Logger:
    logger = logging.getLogger("mellowyak")
    logger.setLevel(logging.INFO)
    for existing in logger.handlers:
        existing.close()
    logger.handlers.clear()
    handler = RotatingFileHandler(
        log_dir / "engine.jsonl", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(RedactingJsonFormatter((session_token,), (data_root,)))
    logger.addHandler(handler)
    logger.propagate = False
    return logger
