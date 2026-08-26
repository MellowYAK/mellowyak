from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mellowyak_engine.compatibility.service import CompatibilityState, assess_project_path
from mellowyak_engine.monitoring.service import MonitoringService
from mellowyak_engine.repair_candidates.manifest import scan_workspace
from mellowyak_engine.runtime_adapters import NodeRuntimeAdapter, PythonRuntimeAdapter
from mellowyak_engine.scanning.policy import FileClassification, classify_path


def test_large_materialized_workspace_is_scannable_before_delta_limits(
    tmp_path: Path,
) -> None:
    for index in range(251):
        (tmp_path / f"source-{index:03}.py").write_text(f"VALUE = {index}\n", encoding="utf-8")

    entries, digest = scan_workspace(tmp_path, enforce_candidate_limits=False)

    assert len(entries) == 251
    assert len(digest) == 64


def test_realistic_file_classification_is_reasoned_and_secret_value_free() -> None:
    cases = {
        "src/app.ts": FileClassification.SOURCE,
        "tests/app.test.ts": FileClassification.TEST,
        "package.json": FileClassification.DEPENDENCY_MANIFEST,
        "pnpm-lock.yaml": FileClassification.DEPENDENCY_LOCK,
        "generated/client.ts": FileClassification.GENERATED,
        "dist/app.js": FileClassification.BUILD_OUTPUT,
        ".pytest_cache/state.json": FileClassification.CACHE,
        ".env.production": FileClassification.SENSITIVE,
        "assets/photo.webp": FileClassification.UNSUPPORTED,
    }

    for relative_path, expected in cases.items():
        classification, reason = classify_path(relative_path)
        assert classification == expected
        assert reason.startswith("file.reason.")
        assert "secret-value-canary" not in reason

    assert classify_path("outside-link", symlink_outside=True) == (
        FileClassification.IGNORED,
        "file.reason.symlink_outside_root",
    )


def test_node_workspace_detection_is_bounded_owned_and_never_runs_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "fixture-workspace",
                "packageManager": "pnpm@10.0.0",
                "scripts": {"dev": "touch forbidden", "test": "vitest run"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - 'packages/*'\n", encoding="utf-8")
    package_root = tmp_path / "packages" / "web"
    package_root.mkdir(parents=True)
    (package_root / "package.json").write_text(
        json.dumps(
            {
                "name": "web",
                "scripts": {"dev": "vite", "test:unit": "vitest run"},
                "dependencies": {"react": "1", "vite": "1", "vitest": "1"},
            }
        ),
        encoding="utf-8",
    )
    invoked: list[tuple[str, ...]] = []

    class MetadataRunner:
        def run(self, **kwargs: object) -> object:
            invoked.append(tuple(kwargs["argv"]))  # type: ignore[arg-type]
            raise FileNotFoundError

    monkeypatch.setattr(
        "mellowyak_engine.runtime_adapters.node.executable_on_path",
        lambda *names: f"/runtime/{names[0]}",
    )

    detections = NodeRuntimeAdapter(runner=MetadataRunner()).detect(tmp_path)  # type: ignore[arg-type]

    assert [item.metadata["runtime_owner"] for item in detections] == [
        "WORKSPACE",
        "WORKSPACE_PACKAGE",
    ]
    assert detections[1].metadata["package_root"] == "packages/web"
    assert detections[1].metadata["package_manager"] == "PNPM"
    assert detections[1].metadata["expected_ports"] == (5173,)
    assert detections[1].metadata["test_frameworks"] == ("VITEST",)
    assert "touch forbidden" not in repr(detections)
    assert invoked == [("--version",)]
    assert not (tmp_path / "forbidden").exists()


def test_python_detection_reports_console_scripts_and_project_confined_commands(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "fixture-python-app"
dependencies = ["flask>=3", "pytest>=8"]

[project.scripts]
fixture = "fixture.cli:main"

[tool.pytest.ini_options]
addopts = "-q"
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("app = object()\n", encoding="utf-8")

    detection = PythonRuntimeAdapter().detect(tmp_path)[0]

    assert detection.metadata["package_manager"] == "UV"
    assert detection.metadata["entry_points"] == ("app.py", "console:fixture")
    assert detection.metadata["frameworks"] == ("FLASK",)
    assert detection.metadata["test_frameworks"] == ("PYTEST",)
    assert detection.metadata["expected_ports"] == (5000,)
    assert all(
        command["relative_working_directory"] == "."
        for command in (
            *detection.metadata["test_commands"],
            *detection.metadata["development_commands"],
        )
    )


def test_gitless_compatibility_is_truthful_and_blocks_symlink_escape(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='gitless'\ndependencies=['pytest']\n", encoding="utf-8"
    )
    (tmp_path / "main.py").write_text("print('local')\n", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.write_text("secret-value-canary", encoding="utf-8")
    link = tmp_path / "outside-link"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")

    result = assess_project_path(tmp_path, project_alias="Gitless fixture")

    assert result["state"] == CompatibilityState.NEEDS_RUNTIME_APPROVAL
    assert "GIT_LESS_PROJECT" in result["detected_structure"]
    assert result["source"] == {
        "path_alias": f"…/{tmp_path.name}",
        "git_available": False,
        "source_remains_local": True,
    }
    ignored = result["inventory"]["classification_samples"]["IGNORED"]
    assert ignored == [{"path": "outside-link", "reason": "file.reason.symlink_outside_root"}]
    assert "secret-value-canary" not in repr(result)
    assert result["external_service_requirement"] == "UNKNOWN_NOT_EXECUTED"


def test_observe_only_state_does_not_claim_automatic_checks(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("observed locally\n", encoding="utf-8")

    result = assess_project_path(tmp_path)

    assert result["state"] == CompatibilityState.OBSERVE_ONLY
    assert result["passive_monitoring_ready"] is True
    assert result["automatic_checks_eligible"] is False
    assert result["safe_next_action"] == "compatibility.action.continue_passive_observation"


def test_watcher_gap_rescan_is_deduplicated_and_uses_current_identity() -> None:
    events: list[tuple[str, str, dict[str, object]]] = []

    class EventBus:
        def publish(self, event: str, project_id: str, payload: dict[str, object]) -> None:
            events.append((event, project_id, payload))

    class Projects:
        events = EventBus()

        def refresh_git(self, project_id: str) -> dict[str, str]:
            return {"worktree_fingerprint": "f" * 64}

    class Scans:
        def start(self, project_id: str) -> str:
            return "queued"

    class Episodes:
        def __init__(self) -> None:
            self.calls: list[tuple[str, list[str]]] = []

        def record(self, project_id: str, paths: list[str]) -> None:
            self.calls.append((project_id, paths))

    episodes = Episodes()
    service = MonitoringService(Projects(), Scans(), episodes)  # type: ignore[arg-type]

    assert service.request_rescan("project-1", "fsevents_gap") == "queued"
    assert episodes.calls == [("project-1", ["."])]
    assert [event for event, _, _ in events] == [
        "watcher_gap_detected",
        "watcher_rescan_requested",
    ]
    assert events[-1][2]["source_fingerprint"] == "f" * 64

    with pytest.raises(ValueError, match="WATCHER_RESCAN_REASON_INVALID"):
        service.request_rescan("project-1", "untrusted-reason")


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink semantics are tested here")
def test_project_local_symlink_is_observed_without_path_escape(tmp_path: Path) -> None:
    source = tmp_path / "source.ts"
    source.write_text("export const value = 1;\n", encoding="utf-8")
    (tmp_path / "source-link.ts").symlink_to(source)

    result = assess_project_path(tmp_path)

    samples = result["inventory"]["classification_samples"]
    assert {item["path"] for item in samples["SOURCE"]} == {"source-link.ts", "source.ts"}
