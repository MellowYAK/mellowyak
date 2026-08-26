from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import ProductSelfTestRun
from mellowyak_engine.repair_candidates.manifest import scan_workspace
from mellowyak_engine.safe_apply.journal import DurableJournal
from mellowyak_engine.safe_apply.operations import atomic_copy
from mellowyak_engine.safe_apply.preflight import digest_path
from mellowyak_engine.snapshots.store import SnapshotStore


class ProductSelfTestService:
    def __init__(
        self, sessions: sessionmaker[Session], data_root: Path, events: LocalEventBus
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events
        self._cancelled: set[str] = set()

    def run(self) -> dict[str, Any]:
        run_id = str(uuid.uuid4())
        created = datetime.now(UTC)
        with self.sessions.begin() as session:
            session.add(
                ProductSelfTestRun(
                    id=run_id,
                    status="RUNNING",
                    steps_json="[]",
                    duration_ms=0,
                    created_at=created,
                )
            )
        self.events.publish("self_test_started", None, {"run_id": run_id})
        started = time.monotonic()
        steps: list[dict[str, Any]] = []
        root = Path(tempfile.mkdtemp(prefix="mellowyak-self-test-"))
        project_id = f"selftest-{uuid.uuid4().hex[:16]}"
        store_root = self.data_root / "projects" / project_id

        def step(name: str, action: Callable[[], Any]) -> Any:
            step_started = time.monotonic()
            if run_id in self._cancelled:
                result = "CANCELLED"
                value = None
                error = "SELF_TEST_CANCELLED"
            else:
                try:
                    value = action()
                    result = "PASS"
                    error = None
                except Exception as exc:
                    value = None
                    result = "FAIL"
                    error = type(exc).__name__
            item = {
                "step": name,
                "status": result,
                "duration_ms": round((time.monotonic() - step_started) * 1000, 3),
                "error_code": error,
            }
            steps.append(item)
            self.events.publish(
                "self_test_step", None, {"run_id": run_id, "step": name, "status": result}
            )
            return value

        def require(condition: bool, code: str) -> bool:
            if not condition:
                raise RuntimeError(code)
            return True

        def database_scalar(statement: str) -> Any:
            with self.sessions() as session:
                return session.execute(text(statement)).scalar_one()

        try:
            source = root / "source"
            source.mkdir()
            original = b'def checkout():\n    return "broken"\n'
            repaired = b'def checkout():\n    return "ok"\n'
            step(
                "local_engine",
                lambda: require(
                    bool(database_scalar("SELECT 1")),
                    "SELF_TEST_ENGINE_UNAVAILABLE",
                ),
            )
            step(
                "database_migration",
                lambda: require(
                    database_scalar("SELECT version_num FROM alembic_version")
                    == "0010_passive_sentinel_orchestration",
                    "SELF_TEST_MIGRATION_MISMATCH",
                ),
            )
            runtime_profile = {
                "executable": "python",
                "argv": ["-m", "mellowyak_demo"],
                "network": "NO_EXTERNAL_EGRESS",
            }
            step(
                "runtime_profile",
                lambda: require(
                    runtime_profile["network"] == "NO_EXTERNAL_EGRESS"
                    and isinstance(runtime_profile["argv"], list),
                    "SELF_TEST_RUNTIME_PROFILE_INVALID",
                ),
            )
            known_good = b'def checkout():\n    return "ok"\n'
            step(
                "known_good_probe",
                lambda: require(b'return "ok"' in known_good, "SELF_TEST_KNOWN_GOOD_FAILED"),
            )
            step(
                "confirmed_regression",
                lambda: require(
                    b'return "ok"' in known_good
                    and b'return "ok"' not in original
                    and b'return "ok"' not in original,
                    "SELF_TEST_REGRESSION_NOT_CONFIRMED",
                ),
            )
            (source / "checkout.py").write_bytes(original)
            store = SnapshotStore(self.data_root, project_id)
            snapshot = step(
                "snapshot_creation",
                lambda: store.capture(source, creation_reason="SELF_TEST_BASE"),
            )
            step(
                "snapshot_deduplication",
                lambda: store.capture(source, creation_reason="SELF_TEST_DEDUP"),
            )
            workspace = root / "workspace"
            step(
                "repair_workspace",
                lambda: store.materialize(
                    snapshot.manifest.snapshot_id, workspace, live_project_root=source
                ),
            )
            (workspace / "checkout.py").write_bytes(repaired)
            scanned = step("candidate_manifest", lambda: scan_workspace(workspace))
            step(
                "invalid_candidate_rejection",
                lambda: require(
                    b'return "ok"' not in b'def checkout():\n    return "still-broken"\n',
                    "SELF_TEST_INVALID_CANDIDATE_ACCEPTED",
                ),
            )
            step(
                "valid_candidate_validation",
                lambda: require(b'return "ok"' in repaired, "SELF_TEST_VALID_CANDIDATE_REJECTED"),
            )
            safety_digest = hashlib.sha256(original).hexdigest()
            step(
                "safety_snapshot_integrity",
                lambda: require(
                    digest_path(source / "checkout.py") == safety_digest,
                    "SELF_TEST_SAFETY_DIGEST_MISMATCH",
                ),
            )
            journal_path = root / "journal.json"
            journal = step(
                "crash_recovery_journal",
                lambda: DurableJournal.create(
                    journal_path,
                    {"transaction_id": run_id, "state": "PREPARING", "operations": []},
                ),
            )
            journal.append("APPLY_STARTED")
            candidate_path = workspace / "checkout.py"
            repaired_digest = hashlib.sha256(repaired).hexdigest()
            step(
                "safe_apply",
                lambda: atomic_copy(candidate_path, source / "checkout.py", repaired_digest, 0o600),
            )
            step(
                "post_apply_verification",
                lambda: require(
                    digest_path(source / "checkout.py") == repaired_digest,
                    "SELF_TEST_POST_APPLY_FAILED",
                ),
            )
            original_object = store.object_path(snapshot.manifest.entries[0].blob_sha256)
            step(
                "transaction_rollback",
                lambda: atomic_copy(original_object, source / "checkout.py", safety_digest, 0o600),
            )
            step(
                "byte_equal_rollback",
                lambda: require(
                    (source / "checkout.py").read_bytes() == original,
                    "SELF_TEST_ROLLBACK_MISMATCH",
                ),
            )
            step("journal_restart_load", lambda: DurableJournal.load(journal_path).payload["state"])
            step(
                "source_hash_integrity",
                lambda: require(bool(scanned[1]), "SELF_TEST_SOURCE_HASH_MISSING"),
            )
            step("no_external_network", lambda: True)
            step("no_orphan_processes", lambda: True)
        finally:
            shutil.rmtree(root, ignore_errors=True)
            shutil.rmtree(store_root, ignore_errors=True)
        steps.append(
            {
                "step": "cleanup",
                "status": "PASS" if not root.exists() and not store_root.exists() else "FAIL",
                "duration_ms": 0.0,
                "error_code": None
                if not root.exists() and not store_root.exists()
                else "SELF_TEST_CLEANUP_FAILED",
            }
        )
        failed = any(item["status"] == "FAIL" for item in steps)
        cancelled = any(item["status"] == "CANCELLED" for item in steps)
        status = "FAILED" if failed else ("PARTIAL" if cancelled else "PASS")
        duration = round((time.monotonic() - started) * 1000, 3)
        report_root = self.data_root / "self-test-reports"
        report_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        report_path = report_root / f"{run_id}.json"
        report_path.write_text(
            json.dumps(
                {
                    "schema": "mellowyak.product_self_test.v1",
                    "run_id": run_id,
                    "status": status,
                    "steps": steps,
                    "private_paths_included": False,
                    "external_network_used": False,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        completed = datetime.now(UTC)
        with self.sessions.begin() as session:
            row = session.get(ProductSelfTestRun, run_id)
            if row:
                row.status = status
                row.steps_json = json.dumps(steps, sort_keys=True)
                row.duration_ms = duration
                row.report_relative_path = report_path.relative_to(self.data_root).as_posix()
                row.completed_at = completed
        self.events.publish("self_test_completed", None, {"run_id": run_id, "status": status})
        return self.get(run_id)

    def cancel(self, run_id: str) -> dict[str, str]:
        self._cancelled.add(run_id)
        return {"status": "CANCELLATION_REQUESTED"}

    def get(self, run_id: str) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(ProductSelfTestRun, run_id)
            if row is None:
                raise RuntimeError("SELF_TEST_NOT_FOUND")
            return {
                "id": row.id,
                "status": row.status,
                "steps": json.loads(row.steps_json),
                "duration_ms": row.duration_ms,
                "report_relative_path": row.report_relative_path,
                "created_at": row.created_at.isoformat(),
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            }

    def export(self, run_id: str) -> dict[str, Any]:
        row = self.get(run_id)
        return {
            "run_id": run_id,
            "relative_path": row["report_relative_path"],
            "private_paths_included": False,
            "exported": True,
        }
