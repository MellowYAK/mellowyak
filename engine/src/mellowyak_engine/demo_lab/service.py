from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.models import DemoLabRun, RepairWorkspace, RepairWorkspaceItem
from mellowyak_engine.demo_lab.template import (
    BAD_REPAIR_SOURCE,
    DEMO_MARKER,
    GOOD_SOURCE,
    REGRESSION_SOURCE,
    create_template,
)
from mellowyak_engine.projects.service import ProjectService
from mellowyak_engine.repair_candidates.service import RepairCandidateService
from mellowyak_engine.repair_validation.service import RepairValidationService
from mellowyak_engine.safe_apply.service import SafeApplyService
from mellowyak_engine.snapshots.service import SnapshotService
from mellowyak_engine.snapshots.store import SnapshotStore


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class DemoLabServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class DemoLabService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        data_root: Path,
        events: LocalEventBus,
        projects: ProjectService,
        snapshots: SnapshotService,
        candidates: RepairCandidateService,
        validations: RepairValidationService,
        safe_apply: SafeApplyService,
    ) -> None:
        self.sessions = sessions
        self.data_root = data_root.resolve()
        self.events = events
        self.projects = projects
        self.snapshots = snapshots
        self.candidates = candidates
        self.validations = validations
        self.safe_apply = safe_apply

    def _run(self, demo_id: str) -> DemoLabRun:
        with self.sessions() as session:
            row = session.get(DemoLabRun, demo_id)
            if row is None:
                raise DemoLabServiceError("DEMO_LAB_NOT_FOUND")
            session.expunge(row)
            return row

    def _root(self, row: DemoLabRun) -> Path:
        root = (self.data_root / row.root_relative_path).resolve(strict=True)
        marker = root / DEMO_MARKER
        if not marker.is_file() or marker.is_symlink():
            raise DemoLabServiceError("DEMO_LAB_MARKER_MISSING")
        payload = json.loads(marker.read_text(encoding="utf-8"))
        if payload.get("demo_id") != row.id:
            raise DemoLabServiceError("DEMO_LAB_MARKER_INVALID")
        return root

    def create(self, selected_parent: str) -> dict[str, Any]:
        parent = Path(selected_parent).expanduser().resolve(strict=True)
        if not parent.is_dir() or not os.access(parent, os.W_OK | os.X_OK):
            raise DemoLabServiceError("DEMO_PARENT_INVALID")
        demo_id = str(uuid.uuid4())
        root = parent / f"MellowYak-Demo-{demo_id[:8]}"
        if root.exists():
            raise DemoLabServiceError("DEMO_ROOT_EXISTS")
        create_template(root, demo_id)
        project = self.projects.create(
            str(root),
            "MellowYak Synthetic Demo",
            "paused",
            project_type="DEMO",
            observation_level="STANDARD",
        )
        baseline = self.snapshots.create(project.id, creation_reason="DEMO_KNOWN_GOOD")
        now = datetime.now(UTC)
        relative_root = (
            root.relative_to(self.data_root).as_posix()
            if root.is_relative_to(self.data_root)
            else ""
        )
        if not relative_root:
            # Persist no absolute selected path. A small data-root pointer resolves through Project.
            relative_root = f"external-demo/{demo_id}"
        with self.sessions.begin() as session:
            session.add(
                DemoLabRun(
                    id=demo_id,
                    project_id=project.id,
                    root_relative_path=relative_root,
                    scenario="KNOWN_GOOD",
                    status="READY",
                    state_json=_json(
                        {
                            "synthetic": True,
                            "baseline_snapshot_id": baseline["id"],
                            "workspace_id": None,
                            "candidate_id": None,
                        }
                    ),
                    created_at=now,
                    updated_at=now,
                )
            )
        # External selected paths are retained only by the existing local Project record.
        self.events.publish("demo_lab_created", project.id, {"demo_id": demo_id})
        return self.get(demo_id)

    def _project_root(self, row: DemoLabRun) -> Path:
        if not row.project_id:
            raise DemoLabServiceError("DEMO_PROJECT_MISSING")
        project = self.projects.get_model(row.project_id)
        root = Path(project.canonical_root_path or project.root_path).resolve(strict=True)
        marker = root / DEMO_MARKER
        if not marker.is_file() or json.loads(marker.read_text()).get("demo_id") != row.id:
            raise DemoLabServiceError("DEMO_LAB_MARKER_INVALID")
        return root

    def _state(self, row: DemoLabRun) -> dict[str, Any]:
        return json.loads(row.state_json or "{}")

    def _update(self, demo_id: str, scenario: str, **updates: Any) -> dict[str, Any]:
        with self.sessions.begin() as session:
            row = session.get(DemoLabRun, demo_id)
            if row is None:
                raise DemoLabServiceError("DEMO_LAB_NOT_FOUND")
            state = self._state(row)
            state.update(updates)
            row.scenario = scenario
            row.state_json = _json(state)
            row.updated_at = datetime.now(UTC)
        self.events.publish(
            "demo_scenario_changed", row.project_id, {"demo_id": demo_id, "scenario": scenario}
        )
        return self.get(demo_id)

    def inject_regression(self, demo_id: str) -> dict[str, Any]:
        row = self._run(demo_id)
        root = self._project_root(row)
        (root / "checkout.py").write_text(REGRESSION_SOURCE, encoding="utf-8")
        snapshot = self.snapshots.create(str(row.project_id), creation_reason="DEMO_REGRESSION")
        workspace_id = self._create_workspace(row, str(snapshot["id"]))
        return self._update(
            demo_id,
            "CONFIRMED_REGRESSION",
            failing_snapshot_id=snapshot["id"],
            workspace_id=workspace_id,
            regression_confirmed=True,
        )

    def _create_workspace(self, row: DemoLabRun, snapshot_id: str) -> str:
        if not row.project_id:
            raise DemoLabServiceError("DEMO_PROJECT_MISSING")
        workspace_id = str(uuid.uuid4())
        root = self.data_root / "projects" / row.project_id / "repair-workspaces" / workspace_id
        root.mkdir(parents=True, mode=0o700)
        (root / "evidence").mkdir(mode=0o700)
        (root / "references").mkdir(mode=0o700)
        store = SnapshotStore(self.data_root, row.project_id)
        manifest = store.load_manifest(snapshot_id)
        store.materialize(snapshot_id, root / "current", live_project_root=self._project_root(row))
        validation_policy = {
            "network": "NO_EXTERNAL_EGRESS",
            "checks": [
                {
                    "id": "original-failed-probe",
                    "type": "FILE_CONTAINS",
                    "path": "checkout.py",
                    "expected": 'return "ok"',
                    "requirement": "REQUIRED",
                },
                {
                    "id": "impacted-checkout-check",
                    "type": "FILE_NOT_CONTAINS",
                    "path": "checkout.py",
                    "expected": "broken",
                    "requirement": "REQUIRED",
                },
            ],
        }
        for name, content in {
            "MELLOWYAK_REPAIR.md": b"# Synthetic Demo Repair Workspace\n",
            "incident.json": b'{"schema":"mellowyak.synthetic_incident.v1"}\n',
            "source-manifest.json": json.dumps(manifest.to_dict(), sort_keys=True).encode() + b"\n",
            "validation-plan.json": _json(validation_policy).encode() + b"\n",
        }.items():
            (root / name).write_bytes(content)
        now = datetime.now(UTC)
        with self.sessions.begin() as session:
            session.add(
                RepairWorkspace(
                    id=workspace_id,
                    project_id=row.project_id,
                    regression_id=None,
                    signal_id=None,
                    snapshot_id=snapshot_id,
                    workspace_relative_path=root.relative_to(self.data_root).as_posix(),
                    manifest_digest=manifest.manifest_digest,
                    base_manifest_digest=manifest.manifest_digest,
                    workspace_manifest_digest=manifest.manifest_digest,
                    runtime_profile_versions_json="[]",
                    validation_policy_json=_json(validation_policy),
                    status="READY",
                    created_at=now,
                    last_change_at=now,
                )
            )
            session.flush()
            for ordinal, name in enumerate(
                [
                    "MELLOWYAK_REPAIR.md",
                    "incident.json",
                    "source-manifest.json",
                    "validation-plan.json",
                    "current",
                ]
            ):
                session.add(
                    RepairWorkspaceItem(
                        id=str(uuid.uuid4()),
                        workspace_id=workspace_id,
                        ordinal=ordinal,
                        item_type="DIRECTORY" if name == "current" else "DOCUMENT",
                        relative_reference=name,
                        reason="SYNTHETIC_DEMO_REQUIRED_ITEM",
                    )
                )
        return workspace_id

    def candidate(self, demo_id: str, *, valid: bool) -> dict[str, Any]:
        row = self._run(demo_id)
        state = self._state(row)
        workspace_id = state.get("workspace_id")
        if not workspace_id or not row.project_id:
            raise DemoLabServiceError("DEMO_REPAIR_WORKSPACE_MISSING")
        workspace_root = (
            self.data_root
            / "projects"
            / row.project_id
            / "repair-workspaces"
            / workspace_id
            / "current"
        )
        (workspace_root / "checkout.py").write_text(
            GOOD_SOURCE if valid else BAD_REPAIR_SOURCE, encoding="utf-8"
        )
        candidate = self.candidates.create(row.project_id, workspace_id)
        validation = self.validations.validate(row.project_id, str(candidate["id"]))
        scenario = "VALID_REPAIR" if valid else "INVALID_REPAIR"
        return self._update(
            demo_id,
            scenario,
            candidate_id=candidate["id"],
            validation_id=validation["id"],
            candidate_state=self.candidates.get(row.project_id, str(candidate["id"]))["state"],
        )

    def simulate_post_apply_failure(self, demo_id: str) -> dict[str, Any]:
        row = self._run(demo_id)
        state = self._state(row)
        if not row.project_id or not state.get("candidate_id"):
            raise DemoLabServiceError("DEMO_VALID_CANDIDATE_MISSING")
        prepared = self.safe_apply.prepare(row.project_id, str(state["candidate_id"]))
        workspace_id = str(state["workspace_id"])
        with self.sessions.begin() as session:
            workspace = session.get(RepairWorkspace, workspace_id)
            if workspace:
                policy = json.loads(workspace.validation_policy_json)
                policy["checks"][0]["expected"] = "DEMO_POST_APPLY_FAILURE"
                workspace.validation_policy_json = _json(policy)
        result = self.safe_apply.confirm(
            row.project_id,
            str(prepared["id"]),
            str(prepared["confirmation_nonce"]),
        )
        return self._update(
            demo_id,
            "ROLLED_BACK_SAFELY",
            transaction_id=result["id"],
            transaction_state=result["state"],
        )

    def apply_valid(self, demo_id: str) -> dict[str, Any]:
        row = self._run(demo_id)
        state = self._state(row)
        if not row.project_id or not state.get("candidate_id"):
            raise DemoLabServiceError("DEMO_VALID_CANDIDATE_MISSING")
        prepared = self.safe_apply.prepare(row.project_id, str(state["candidate_id"]))
        result = self.safe_apply.confirm(
            row.project_id,
            str(prepared["id"]),
            str(prepared["confirmation_nonce"]),
        )
        return self._update(
            demo_id,
            "APPLIED_AND_VERIFIED",
            transaction_id=result["id"],
            transaction_state=result["state"],
        )

    def reset(self, demo_id: str) -> dict[str, Any]:
        row = self._run(demo_id)
        root = self._project_root(row)
        (root / "checkout.py").write_text(GOOD_SOURCE, encoding="utf-8")
        snapshot = self.snapshots.create(str(row.project_id), creation_reason="DEMO_RESET")
        return self._update(
            demo_id,
            "KNOWN_GOOD",
            reset_snapshot_id=snapshot["id"],
            workspace_id=None,
            candidate_id=None,
            validation_id=None,
            transaction_id=None,
        )

    def get(self, demo_id: str) -> dict[str, Any]:
        row = self._run(demo_id)
        return {
            "id": row.id,
            "project_id": row.project_id,
            "synthetic": True,
            "scenario": row.scenario,
            "status": row.status,
            "state": self._state(row),
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
        }
