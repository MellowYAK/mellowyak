from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any

import pytest

from mellowyak_engine.behaviors.service import BehaviorService
from mellowyak_engine.core.events import LocalEventBus
from mellowyak_engine.db.database import LocalDatabase
from mellowyak_engine.db.models import ProbeRun, Project, SourceEpisode
from mellowyak_engine.git import observer
from mellowyak_engine.probes.adapters import (
    CliProbeAdapter,
    ProbeRequest,
    ProcessHealthProbeAdapter,
)
from mellowyak_engine.probes.service import ProbeService, ProbeServiceError
from mellowyak_engine.runtime_profiles.service import (
    RuntimeProfileService,
    RuntimeProfileServiceError,
)
from mellowyak_engine.snapshots.service import SnapshotService
from mellowyak_engine.storage.paths import StoragePaths

PROJECT_A = "11111111-1111-4111-8111-111111111111"
PROJECT_B = "22222222-2222-4222-8222-222222222222"
PRIVATE_DIRECTORIES = frozenset({".aws", ".codex", ".mcp", ".ssh"})


def _write_with_original_open(
    original_open: Any, path: Path, value: str, *, encoding: str = "utf-8"
) -> None:
    with original_open(path, "w", encoding=encoding) as handle:
        handle.write(value)


def _guard_private_file_opens(monkeypatch: pytest.MonkeyPatch) -> Any:
    original_open = Path.open

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if PRIVATE_DIRECTORIES.intersection(path.parts):
            raise AssertionError(f"private provider file was opened: {path}")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    return original_open


def _create_private_provider_files(root: Path) -> list[Path]:
    paths = []
    for directory in sorted(PRIVATE_DIRECTORIES):
        path = root / directory / "private-provider-data"
        path.parent.mkdir(parents=True)
        path.write_text(f"private:{directory}\n", encoding="utf-8")
        paths.append(path)
    return paths


def test_non_git_fingerprint_never_enters_or_opens_private_provider_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "plain-project"
    root.mkdir()
    (root / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    private_paths = _create_private_provider_files(root)
    original_scandir = os.scandir

    def guarded_scandir(path: Any) -> Any:
        candidate = Path(path)
        if PRIVATE_DIRECTORIES.intersection(candidate.parts):
            raise AssertionError(f"private provider directory was entered: {candidate}")
        return original_scandir(path)

    monkeypatch.setattr(observer.os, "scandir", guarded_scandir)
    original_open = _guard_private_file_opens(monkeypatch)

    before = observer.observe_git(root)
    for index, private_path in enumerate(private_paths):
        _write_with_original_open(original_open, private_path, f"changed-private-data-{index}\n")
    after = observer.observe_git(root)

    assert before.available is False
    assert after.available is False
    assert after.worktree_fingerprint == before.worktree_fingerprint


def test_git_fingerprint_never_opens_private_provider_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "git-project"
    root.mkdir()
    (root / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "source.py"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=MellowYak Tests",
            "-c",
            "user.email=tests@mellowyak.invalid",
            "commit",
            "--quiet",
            "-m",
            "fixture",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    private_paths = _create_private_provider_files(root)
    original_open = _guard_private_file_opens(monkeypatch)

    before = observer.observe_git(root)
    for index, private_path in enumerate(private_paths):
        _write_with_original_open(original_open, private_path, f"changed-private-data-{index}\n")
    after = observer.observe_git(root)

    assert before.available is True
    assert after.available is True
    assert after.worktree_fingerprint == before.worktree_fingerprint


@pytest.mark.parametrize(
    ("adapter", "executable"),
    [
        (CliProbeAdapter(), "sh"),
        (CliProbeAdapter(), "/bin/bash"),
        (ProcessHealthProbeAdapter(), "sh"),
        (ProcessHealthProbeAdapter(), "/bin/bash"),
    ],
)
def test_cli_and_process_probes_reject_shell_executables(
    tmp_path: Path,
    adapter: CliProbeAdapter | ProcessHealthProbeAdapter,
    executable: str,
) -> None:
    request = ProbeRequest(
        project_root=tmp_path,
        probe_type=adapter.probe_type,
        definition={"executable": executable, "argv": []},
    )

    with pytest.raises(ValueError, match="^PROBE_SHELL_EXECUTABLE_DENIED$"):
        adapter.run(request, Event())


@dataclass
class ServiceRig:
    paths: StoragePaths
    database: LocalDatabase
    root_a: Path
    root_b: Path
    snapshots: SnapshotService
    runtimes: RuntimeProfileService
    probes: ProbeService
    behaviors: BehaviorService


@pytest.fixture
def service_rig(tmp_path: Path) -> ServiceRig:
    root_a = tmp_path / "project-a"
    root_b = tmp_path / "project-b"
    root_a.mkdir()
    root_b.mkdir()
    (root_a / "source.py").write_text("VALUE = 'a'\n", encoding="utf-8")
    (root_b / "source.py").write_text("VALUE = 'b'\n", encoding="utf-8")
    paths = StoragePaths.create(tmp_path / "mellowyak-data")
    database = LocalDatabase(paths)
    database.migrate()
    now = datetime.now(UTC)
    with database.sessions.begin() as session:
        for project_id, display_name, root in (
            (PROJECT_A, "Project A", root_a),
            (PROJECT_B, "Project B", root_b),
        ):
            session.add(
                Project(
                    id=project_id,
                    display_name=display_name,
                    root_path=str(root),
                    canonical_root_path=str(root.resolve()),
                    repository_root_path=None,
                    created_at=now,
                    updated_at=now,
                    monitoring_mode="paused",
                    monitoring_status="paused",
                    current_branch=None,
                    current_head_sha=None,
                    current_worktree_fingerprint=None,
                    detection_payload_json="{}",
                )
            )
    events = LocalEventBus()
    snapshots = SnapshotService(database.sessions, paths.root, events)
    rig = ServiceRig(
        paths=paths,
        database=database,
        root_a=root_a,
        root_b=root_b,
        snapshots=snapshots,
        runtimes=RuntimeProfileService(database.sessions, events),
        probes=ProbeService(database.sessions, events, snapshots),
        behaviors=BehaviorService(database.sessions, events),
    )
    try:
        yield rig
    finally:
        database.engine.dispose()


def _runtime_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "display_name": "Focused runtime",
        "runtime_type": "GENERIC_PROCESS",
        "primary": False,
        "execution_mode": "MANAGED",
        "executable_reference": sys.executable,
        "argv": ["-c", "print('ok')"],
        "relative_working_directory": ".",
        "runtime_version": None,
        "dependency_fingerprint": None,
        "health_definition": {},
        "expected_ports": [],
        "test_definitions": [],
        "environment_schema": [],
        "network_policy": "LOOPBACK_ONLY",
        "limitations": [],
        "approved": True,
    }
    payload.update(overrides)
    return payload


def _create_probe(
    rig: ServiceRig,
    project_id: str,
    *,
    display_name: str,
    probe_type: str,
    definition: dict[str, Any],
    expected_result: dict[str, Any],
    behavior_id: str | None = None,
    runtime_profile_version_id: str | None = None,
) -> dict[str, Any]:
    return rig.probes.create(
        project_id,
        display_name=display_name,
        probe_type=probe_type,
        behavior_id=behavior_id,
        runtime_profile_version_id=runtime_profile_version_id,
        definition=definition,
        timeout_seconds=3,
        retry_policy={},
        expected_result=expected_result,
        evidence_policy={},
        source_links=[],
        runtime_links=[],
        approved=True,
    )


def _encoded_output_script(stdout: str, stderr: str, *, sleep_seconds: int = 0) -> str:
    return (
        "import sys,time;"
        f"print(bytes({list(stdout.encode())}).decode(),flush=True);"
        f"print(bytes({list(stderr.encode())}).decode(),file=sys.stderr,flush=True);"
        f"time.sleep({sleep_seconds})"
    )


def test_cli_and_process_probe_runs_persist_only_output_metadata(service_rig: ServiceRig) -> None:
    snapshot = service_rig.snapshots.create(PROJECT_A, creation_reason="PROBE_SECURITY_TEST")
    cases = (
        (
            "CLI",
            "PHASE7_RAW_CLI_STDOUT_7921",
            "PHASE7_RAW_CLI_STDERR_7922",
            {"exit_code": 0},
            0,
        ),
        (
            "PROCESS",
            "PHASE7_RAW_PROCESS_STDOUT_7923",
            "PHASE7_RAW_PROCESS_STDERR_7924",
            {"alive_seconds": 0.1},
            5,
        ),
    )

    for probe_type, raw_stdout, raw_stderr, expected, sleep_seconds in cases:
        probe = _create_probe(
            service_rig,
            PROJECT_A,
            display_name=f"{probe_type} output metadata",
            probe_type=probe_type,
            definition={
                "executable": sys.executable,
                "argv": [
                    "-c",
                    _encoded_output_script(raw_stdout, raw_stderr, sleep_seconds=sleep_seconds),
                ],
            },
            expected_result=expected,
        )

        run = service_rig.probes.run(PROJECT_A, probe["id"], snapshot["id"])

        assert run["result"] == "PASS"
        assert set(run["evidence"]) == {
            "stderr_bytes",
            "stderr_sha256",
            "stderr_truncated",
            "stdout_bytes",
            "stdout_sha256",
            "stdout_truncated",
        }
        assert run["evidence"]["stdout_bytes"] > 0
        assert run["evidence"]["stderr_bytes"] > 0
        serialized_evidence = json.dumps(run["evidence"], sort_keys=True)
        assert raw_stdout not in serialized_evidence
        assert raw_stderr not in serialized_evidence
        with service_rig.database.sessions() as session:
            stored = session.get(ProbeRun, run["id"])
            assert stored is not None
            assert raw_stdout not in stored.evidence_json
            assert raw_stderr not in stored.evidence_json
            assert json.loads(stored.evidence_json) == run["evidence"]


def test_runtime_profile_service_rejects_unsafe_execution_boundaries(
    service_rig: ServiceRig,
) -> None:
    invalid_cases = (
        (
            {"relative_working_directory": "../project-b"},
            "RUNTIME_WORKING_DIRECTORY_INVALID",
        ),
        (
            {"environment_schema": ["MELLOWYAK_API_TOKEN"]},
            "RUNTIME_ENVIRONMENT_SECRET_NAME_DENIED",
        ),
        ({"expected_ports": [0]}, "RUNTIME_EXPECTED_PORT_INVALID"),
        ({"expected_ports": [65536]}, "RUNTIME_EXPECTED_PORT_INVALID"),
        ({"expected_ports": [True]}, "RUNTIME_EXPECTED_PORT_INVALID"),
        ({"network_policy": "OUTBOUND_ALLOWED"}, "RUNTIME_NETWORK_POLICY_DENIED"),
    )

    for overrides, expected_code in invalid_cases:
        with pytest.raises(RuntimeProfileServiceError) as caught:
            service_rig.runtimes.create_or_version(
                PROJECT_A,
                **_runtime_payload(**overrides),
            )
        assert caught.value.code == expected_code


def test_probe_service_rejects_cross_project_links_and_returns_semantic_impact_reason(
    service_rig: ServiceRig,
) -> None:
    runtime_b = service_rig.runtimes.create_or_version(PROJECT_B, **_runtime_payload())
    with pytest.raises(ProbeServiceError) as runtime_error:
        _create_probe(
            service_rig,
            PROJECT_A,
            display_name="Cross-project runtime",
            probe_type="MANUAL",
            definition={"confirmed": True},
            expected_result={},
            runtime_profile_version_id=runtime_b["current_version_id"],
        )
    assert runtime_error.value.code == "RUNTIME_PROFILE_VERSION_NOT_FOUND"

    behavior_b = service_rig.behaviors.create_draft(
        PROJECT_B,
        "Project B behavior",
        "",
        "",
    )
    probe_b = _create_probe(
        service_rig,
        PROJECT_B,
        display_name="Project B probe",
        probe_type="MANUAL",
        definition={"confirmed": True},
        expected_result={},
        behavior_id=behavior_b["id"],
    )
    snapshot_a = service_rig.snapshots.create(PROJECT_A, creation_reason="LINK_SECURITY_TEST")

    with pytest.raises(ProbeServiceError) as behavior_version_error:
        service_rig.probes.create_milestone(
            PROJECT_A,
            snapshot_a["id"],
            "Cross-project behavior version",
            behavior_id=None,
            behavior_version_id=behavior_b["current_version_id"],
            probe_version_id=None,
            human_attested=True,
        )
    assert behavior_version_error.value.code == "BEHAVIOR_VERSION_NOT_FOUND"

    with pytest.raises(ProbeServiceError) as probe_version_error:
        service_rig.probes.create_milestone(
            PROJECT_A,
            snapshot_a["id"],
            "Cross-project probe version",
            behavior_id=None,
            behavior_version_id=None,
            probe_version_id=probe_b["current_version_id"],
            human_attested=True,
        )
    assert probe_version_error.value.code == "PROBE_VERSION_NOT_FOUND"

    behavior_a = service_rig.behaviors.create_draft(
        PROJECT_A,
        "Semantic impact reason",
        "",
        "",
        links=[
            {
                "link_type": "FILE",
                "link_key": "src/service.py",
                "provenance": "HUMAN_CONFIRMED",
            }
        ],
    )
    probe_a = _create_probe(
        service_rig,
        PROJECT_A,
        display_name="Semantic impact probe",
        probe_type="MANUAL",
        definition={"confirmed": True},
        expected_result={},
        behavior_id=behavior_a["id"],
    )
    episode_id = "33333333-3333-4333-8333-333333333333"
    now = datetime.now(UTC)
    with service_rig.database.sessions.begin() as session:
        session.add(
            SourceEpisode(
                id=episode_id,
                project_id=PROJECT_A,
                started_at=now,
                ended_at=now,
                event_count=1,
                added_paths_json="[]",
                modified_paths_json='["src/service.py"]',
                deleted_paths_json="[]",
                renamed_paths_json="[]",
                dependency_changes_json="[]",
                runtime_events_json="[]",
                git_anchor_json="{}",
                status="STABILIZED",
            )
        )

    impacted = service_rig.probes.select_impacted(PROJECT_A, episode_id)

    assert impacted["selected_count"] == 1
    assert impacted["selected"][0]["probe_id"] == probe_a["id"]
    assert impacted["selected"][0]["reason"] == "BEHAVIOR_LINK_HUMAN_CONFIRMED"
    assert impacted["selected"][0]["reason"] != probe_a["id"]
