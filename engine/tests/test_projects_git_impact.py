from __future__ import annotations

import subprocess
import time
from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.git.observer import observe_git
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase-two-session-token-that-is-long-enough-12345"


def git(repo: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True, text=True)


def repository(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "MellowYak Test")
    git(root, "config", "user.email", "test@mellowyak.invalid")
    (root / "package.json").write_text(
        '{"dependencies":{"react":"19"},"devDependencies":{"vitest":"3"}}',
        encoding="utf-8",
    )
    source = root / "src"
    source.mkdir()
    (source / "helper.ts").write_text("export function helper() { return 42; }\n", encoding="utf-8")
    (source / "main.ts").write_text(
        'import { helper } from "./helper";\nexport const answer = helper();\n',
        encoding="utf-8",
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "main.test.ts").write_text(
        'import { answer } from "../src/main";\nvoid answer;\n', encoding="utf-8"
    )
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    return root


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def wait_for_scan(client: TestClient, project_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/projects/{project_id}", headers=headers())
        assert response.status_code == 200
        project = response.json()
        scan = project["scan"]
        if scan and scan["status"] != "running":
            return project
        time.sleep(0.05)
    raise AssertionError("Project scan did not finish")


def test_git_observer_reports_clean_staged_unstaged_and_untracked(tmp_path: Path) -> None:
    root = repository(tmp_path)
    clean = observe_git(root)
    assert clean.available is True
    assert clean.branch == "main"
    assert clean.is_dirty is False
    assert clean.head_sha and len(clean.head_sha) == 40

    (root / "src" / "main.ts").write_text("export const answer = 7;\n", encoding="utf-8")
    (root / "untracked.txt").write_text("local only\n", encoding="utf-8")
    dirty = observe_git(root)
    assert dirty.is_dirty is True
    assert "src/main.ts" in dirty.unstaged
    assert "untracked.txt" in dirty.untracked
    assert dirty.worktree_fingerprint != clean.worktree_fingerprint

    git(root, "add", "src/main.ts")
    staged = observe_git(root)
    assert any(path.endswith(":src/main.ts") for path in staged.staged)
    assert "src/main.ts" not in staged.unstaged


def test_project_api_persists_scan_and_real_impact_without_source_copy(
    tmp_path: Path, create_symlink
) -> None:
    root = repository(tmp_path)
    data_root = tmp_path / "local-data"
    secret = "SOURCE-CONTENT-MUST-NOT-BE-COPIED-91f8"
    (root / ".env").write_text(f"SECRET={secret}\n", encoding="utf-8")
    (root / "large.ts").write_bytes(b"x" * 1_000_001)
    outside = tmp_path / "outside.txt"
    outside.write_text(secret, encoding="utf-8")
    create_symlink(root / "outside-link", outside)
    ignored = root / "dist"
    ignored.mkdir()
    (ignored / "ignored.js").write_text(secret, encoding="utf-8")

    settings = EngineSettings(data_root=data_root, session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        detection = client.post("/projects/detect", headers=headers(), json={"path": str(root)})
        assert detection.status_code == 200
        detected = detection.json()
        assert detected["selected_path"] == str(root.resolve())
        assert detected["git"]["branch"] == "main"
        assert "TypeScript" in detected["languages"]
        assert "React" in detected["frameworks"]
        assert "Vitest" in detected["tests"]
        assert detected["source_remains_local"] is True

        created = client.post(
            "/projects",
            headers=headers(),
            json={"path": str(root), "display_name": "Fixture", "monitoring_mode": "paused"},
        )
        assert created.status_code == 200
        project_id = created.json()["id"]
        project = wait_for_scan(client, project_id)
        assert project["scan"]["status"] == "completed"
        assert project["scan"]["sensitive_files"] == 1
        assert project["scan"]["excluded_files"] >= 3
        assert project["scan"]["test_files"] >= 1

        summary = client.get(f"/projects/{project_id}/impact/summary", headers=headers()).json()
        assert summary["files_indexed"] >= 4
        assert summary["direct_relationships"] >= 2
        assert summary["tests_found"] >= 1
        findings = client.get(f"/projects/{project_id}/findings", headers=headers()).json()[
            "findings"
        ]
        codes = {item["code"] for item in findings}
        assert {"OVERSIZED_FILE", "SYMLINK_OUTSIDE_ROOT"} <= codes

    with TestClient(create_app(settings)) as restarted:
        saved = restarted.get("/projects", headers=headers()).json()["projects"]
        assert [item["id"] for item in saved] == [project_id]
        assert saved[0]["scan"]["status"] == "completed"

    for path in data_root.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()


def test_project_boundaries_reject_duplicates_and_non_directories(tmp_path: Path) -> None:
    root = repository(tmp_path)
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        payload = {"path": str(root), "display_name": "Fixture", "monitoring_mode": "paused"}
        assert client.post("/projects", headers=headers(), json=payload).status_code == 200
        duplicate = client.post("/projects", headers=headers(), json=payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == "PROJECT_ALREADY_CONNECTED"
        file_response = client.post(
            "/projects/detect", headers=headers(), json={"path": str(root / "package.json")}
        )
        assert file_response.status_code == 400
        assert file_response.json()["detail"] == "PROJECT_PATH_NOT_DIRECTORY"
