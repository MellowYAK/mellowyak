from __future__ import annotations

import json
import socket
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from mellowyak_engine.api.app import create_app
from mellowyak_engine.db.database import LocalDatabase, _alembic_config_path
from mellowyak_engine.impact.models import EdgeFact, NodeFact, TraversalPolicy
from mellowyak_engine.impact.ranking import rank_result
from mellowyak_engine.impact.traversal import traverse
from mellowyak_engine.settings.config import EngineSettings
from mellowyak_engine.storage.paths import StoragePaths

TOKEN = "phase-three-session-token-that-is-long-enough-12345"


def git(repo: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=repo, check=True, capture_output=True, text=True)


def repository(tmp_path: Path, name: str = "source") -> Path:
    root = tmp_path / name
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "MellowYak Test")
    git(root, "config", "user.email", "test@mellowyak.invalid")
    src = root / "src"
    src.mkdir()
    (src / "formatTime.ts").write_text(
        "export function formatTime(value: string) { return value; }\n", encoding="utf-8"
    )
    (src / "RescheduleModal.tsx").write_text(
        'import { formatTime } from "./formatTime";\nexport const Modal = formatTime("14:00");\n',
        encoding="utf-8",
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "reschedule.spec.ts").write_text(
        'import { Modal } from "../src/RescheduleModal";\nvoid Modal;\n', encoding="utf-8"
    )
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    return root


def headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def wait_for_scan(client: TestClient, project_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        project = client.get(f"/projects/{project_id}", headers=headers()).json()
        if project.get("scan") and project["scan"]["status"] != "running":
            return project
        time.sleep(0.05)
    raise AssertionError("scan timeout")


def connect(client: TestClient, root: Path, name: str = "Fixture") -> str:
    response = client.post(
        "/projects",
        headers=headers(),
        json={"path": str(root), "display_name": name, "monitoring_mode": "paused"},
    )
    assert response.status_code == 200, response.text
    project_id = response.json()["id"]
    assert wait_for_scan(client, project_id)["scan"]["status"] == "completed"
    return project_id


def graph() -> tuple[list[NodeFact], list[EdgeFact]]:
    nodes = [
        NodeFact("changed", "FILE", "formatTime.ts", "src/formatTime.ts"),
        NodeFact("modal", "FILE", "RescheduleModal.tsx", "src/RescheduleModal.tsx"),
        NodeFact("test", "TEST", "reschedule.spec.ts", "tests/reschedule.spec.ts"),
        NodeFact("unknown", "UNKNOWN_REFERENCE", "dynamic-loader", "src/RescheduleModal.tsx"),
        NodeFact("stale", "FILE", "OldPanel.tsx", "src/OldPanel.tsx", stale=True),
    ]
    edges = [
        EdgeFact("e1", "modal", "changed", "IMPORTS", "STATIC_PARSED", "ecma", "scan-1"),
        EdgeFact("e2", "test", "modal", "IMPORTS", "STATIC_PARSED", "ecma", "scan-1"),
        EdgeFact(
            "e3", "modal", "unknown", "UNKNOWN_RELATION", "STATIC_HEURISTIC", "ecma", "scan-1"
        ),
        EdgeFact(
            "e4", "stale", "changed", "IMPORTS", "STATIC_PARSED", "ecma", "scan-0", stale=True
        ),
    ]
    return nodes, edges


def test_reverse_traversal_finds_direct_two_hop_paths_and_explains_facts() -> None:
    nodes, edges = graph()
    outcome = traverse(nodes, edges, ["changed"])
    by_id = {item.node.id: item for item in outcome.results}
    assert by_id["changed"].impact_class == "CHANGED"
    assert by_id["modal"].impact_class == "DIRECTLY_RELATED"
    assert by_id["test"].impact_class == "TRANSITIVELY_RELATED"
    assert by_id["test"].minimum_depth == 2
    assert "STATIC_PARSED" in by_id["test"].explanation
    assert [step.edge_type for step in by_id["test"].paths[0]] == ["IMPORTS", "IMPORTS"]


@pytest.mark.parametrize(
    ("policy", "reason"),
    [
        (TraversalPolicy(max_depth=1), "maximum traversal depth reached"),
        (TraversalPolicy(max_result_nodes=2), "maximum result nodes reached"),
        (TraversalPolicy(max_explanation_bytes=1_024), None),
    ],
)
def test_traversal_bounds_are_deterministic_and_visible(
    policy: TraversalPolicy, reason: str | None
) -> None:
    nodes, edges = graph()
    first = traverse(nodes, edges, ["changed"], policy)
    second = traverse(nodes, edges, ["changed"], policy)
    assert [(item.node.id, item.impact_class) for item in first.results] == [
        (item.node.id, item.impact_class) for item in second.results
    ]
    assert first.truncation_reasons == second.truncation_reasons
    if reason:
        assert reason in first.truncation_reasons


def test_unknown_and_stale_relations_are_terminal_and_explicit() -> None:
    nodes, edges = graph()
    outcome = traverse(nodes, edges, ["changed"])
    by_id = {item.node.id: item for item in outcome.results}
    assert by_id["unknown"].impact_class == "UNKNOWN_BOUNDARY"
    assert by_id["unknown"].unknown is True
    assert by_id["unknown"].paths[0][-1].edge_type == "UNKNOWN_RELATION"
    assert by_id["stale"].impact_class == "STALE_RELATION"
    assert by_id["stale"].stale is True


def test_ranking_prioritizes_changed_parsed_test_and_intent_without_embeddings() -> None:
    nodes, edges = graph()
    results = traverse(nodes, edges, ["changed"]).results
    for result in results:
        result.ranking_score, result.ranking_reasons = rank_result(
            result, "Fix reschedule timezone display", {"src/formatTime.ts"}
        )
    by_id = {item.node.id: item for item in results}
    assert by_id["changed"].ranking_score > by_id["modal"].ranking_score
    assert "test relationship" in by_id["test"].ranking_reasons
    assert any("intent token overlap" in reason for reason in by_id["test"].ranking_reasons)
    assert "stale relationship penalty" in by_id["stale"].ranking_reasons


def test_change_identity_impact_receipt_candidates_and_restart_persist(tmp_path: Path) -> None:
    root = repository(tmp_path)
    data = tmp_path / "data"
    settings = EngineSettings(data_root=data, session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        source = root / "src" / "formatTime.ts"
        source.write_text(
            "export function formatTime(value: string) { return `local:${value}`; }\n",
            encoding="utf-8",
        )
        first = client.get(f"/projects/{project_id}/changes/current", headers=headers())
        assert first.status_code == 200
        change = first.json()
        assert change["change_kind"] == "uncommitted_worktree"
        assert change["changed_paths"] == ["src/formatTime.ts"]
        repeated = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        assert repeated["id"] == change["id"]
        assert repeated["revision"] == change["revision"]

        intent = client.post(
            f"/projects/{project_id}/changes/{change['id']}/intent",
            headers=headers(),
            json={"intent": "Fix timezone display in meeting reschedule"},
        )
        assert intent.status_code == 200
        analyzed = client.post(
            f"/projects/{project_id}/changes/{change['id']}/analyze",
            headers=headers(),
            json={"max_heuristic_depth": 2},
        )
        assert analyzed.status_code == 200, analyzed.text
        payload = analyzed.json()
        classes = {
            (item["node_type"], item["relative_path"]): item["impact_class"]
            for item in payload["results"]
        }
        assert classes[("FILE", "src/formatTime.ts")] == "CHANGED"
        assert classes[("FILE", "src/RescheduleModal.tsx")] == "HEURISTICALLY_RELATED"
        assert classes[("TEST", "tests/reschedule.spec.ts")] == "HEURISTICALLY_RELATED"
        assert payload["analysis"]["scan_revision"]
        assert payload["analysis"]["algorithm_version"] == "reverse-impact-v1"

        paths = client.get(
            f"/projects/{project_id}/changes/{change['id']}/impact/paths", headers=headers()
        ).json()["paths"]
        assert any(path["depth"] == 2 for path in paths)
        receipt_response = client.post(
            f"/projects/{project_id}/changes/{change['id']}/context-receipt",
            headers=headers(),
            json={},
        )
        assert receipt_response.status_code == 200, receipt_response.text
        receipt = receipt_response.json()
        assert receipt["schema"] == "mellowyak.context_receipt.v1"
        assert receipt["source_uploaded"] is False
        assert receipt["size_metrics"]["selected_source_bytes"] == 0
        assert all(not item["relative_path"].startswith("/") for item in receipt["selected_files"])
        assert all(item["reason_selected"] for item in receipt["selected_files"])
        same_receipt = client.post(
            f"/projects/{project_id}/changes/{change['id']}/context-receipt",
            headers=headers(),
            json={},
        ).json()
        assert same_receipt == receipt

        candidates = client.get(
            f"/projects/{project_id}/behavior-candidates", headers=headers()
        ).json()["candidates"]
        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate["status"] == "CANDIDATE"
        assert candidate["verification"] == "not_configured"
        dismissed = client.post(
            f"/projects/{project_id}/behavior-candidates/{candidate['id']}/dismiss",
            headers=headers(),
            json={},
        ).json()
        assert dismissed["status"] == "DISMISSED"
        kept = client.post(
            f"/projects/{project_id}/behavior-candidates/{candidate['id']}/keep",
            headers=headers(),
            json={},
        ).json()
        assert kept["status"] == "CANDIDATE"
        analysis_id = payload["analysis"]["id"]

    with TestClient(create_app(settings)) as restarted:
        impact = restarted.get(
            f"/projects/{project_id}/changes/{change['id']}/impact", headers=headers()
        )
        assert impact.status_code == 200
        assert impact.json()["analysis"]["id"] == analysis_id
        saved_receipt = restarted.get(
            f"/projects/{project_id}/changes/{change['id']}/context-receipt", headers=headers()
        )
        assert saved_receipt.status_code == 200


def test_changed_fingerprint_creates_new_revision_and_stales_prior_analysis(tmp_path: Path) -> None:
    root = repository(tmp_path)
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        source = root / "src" / "formatTime.ts"
        source.write_text("export const value = 1;\n", encoding="utf-8")
        first = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        analysis = client.post(
            f"/projects/{project_id}/changes/{first['id']}/analyze", headers=headers(), json={}
        ).json()
        source.write_text("export const value = 2;\n", encoding="utf-8")
        second = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        assert second["id"] != first["id"]
        assert second["revision"] == first["revision"] + 1
        stale = client.get(
            f"/projects/{project_id}/changes/{first['id']}/impact", headers=headers()
        ).json()
        assert stale["analysis"]["id"] == analysis["analysis"]["id"]
        assert stale["analysis"]["stale"] is True
        assert "git_change_identity_changed" in stale["analysis"]["stale_reasons"]


def test_clean_committed_change_uses_stable_base_to_head_identity(tmp_path: Path) -> None:
    root = repository(tmp_path)
    initial_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        (root / "src" / "formatTime.ts").write_text("export const committed = true;\n")
        git(root, "add", ".")
        git(root, "commit", "-m", "committed change")
        new_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
        first = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        second = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        assert first["change_kind"] == "committed"
        assert first["base_head_sha"] == initial_head
        assert first["head_sha"] == new_head
        assert first["changed_paths"] == ["src/formatTime.ts"]
        assert second["id"] == first["id"]


def test_new_scan_revision_marks_prior_analysis_stale(tmp_path: Path) -> None:
    root = repository(tmp_path)
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        (root / "src" / "formatTime.ts").write_text("export const changed = 1;\n")
        change = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        analysis = client.post(
            f"/projects/{project_id}/changes/{change['id']}/analyze", headers=headers(), json={}
        ).json()
        scan_response = client.post(f"/projects/{project_id}/scan", headers=headers(), json={})
        assert scan_response.status_code == 200
        wait_for_scan(client, project_id)
        stale = client.get(
            f"/projects/{project_id}/changes/{change['id']}/impact", headers=headers()
        ).json()
        assert stale["analysis"]["id"] == analysis["analysis"]["id"]
        assert stale["analysis"]["stale"] is True
        assert "scan_revision_changed" in stale["analysis"]["stale_reasons"]


def test_context_receipt_enforces_file_budget_and_reports_exclusions(tmp_path: Path) -> None:
    root = repository(tmp_path)
    for index in range(28):
        (root / "src" / f"consumer{index}.ts").write_text(
            f'import {{ formatTime }} from "./formatTime";\n'
            f'export const value{index} = formatTime("x");\n'
        )
    git(root, "add", ".")
    git(root, "commit", "-m", "many consumers")
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        (root / "src" / "formatTime.ts").write_text("export const formatTime = String;\n")
        change = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        client.post(
            f"/projects/{project_id}/changes/{change['id']}/analyze", headers=headers(), json={}
        )
        receipt = client.post(
            f"/projects/{project_id}/changes/{change['id']}/context-receipt",
            headers=headers(),
            json={},
        ).json()
        assert receipt["size_metrics"]["selected_files"] <= 20
        assert receipt["constraints"]["max_files"] == 20
        assert receipt["truncated"] is True
        assert any(item["reason"] == "file_budget" for item in receipt["excluded_context"])


def test_phase3_local_events_are_emitted_without_claiming_protection(tmp_path: Path) -> None:
    root = repository(tmp_path)
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        (root / "src" / "formatTime.ts").write_text("export const changed = 1;\n")
        change = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        client.post(
            f"/projects/{project_id}/changes/{change['id']}/analyze",
            headers=headers(),
            json={"max_heuristic_depth": 2},
        )
        client.post(
            f"/projects/{project_id}/changes/{change['id']}/context-receipt",
            headers=headers(),
            json={},
        )
        events = client.get("/events", headers=headers(), params={"after": 0}).json()["events"]
        event_types = {event["event_type"] for event in events}
        assert {
            "change_stabilized",
            "impact_analysis_started",
            "impact_analysis_completed",
            "context_receipt_generated",
            "behavior_candidate_discovered",
        }.issubset(event_types)
        assert all("protected" not in json.dumps(event["payload"]).lower() for event in events)


def test_prepare_candidate_creates_only_an_unverified_stub(tmp_path: Path) -> None:
    root = repository(tmp_path)
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        (root / "src" / "formatTime.ts").write_text("export const changed = 1;\n")
        change = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        client.post(
            f"/projects/{project_id}/changes/{change['id']}/analyze",
            headers=headers(),
            json={"max_heuristic_depth": 2},
        )
        candidate = client.get(
            f"/projects/{project_id}/behavior-candidates", headers=headers()
        ).json()["candidates"][0]
        prepared = client.post(
            f"/projects/{project_id}/behavior-candidates/{candidate['id']}/prepare",
            headers=headers(),
            json={},
        ).json()
        assert prepared["id"] == candidate["id"]
        assert prepared["status"] == "PROMOTED_STUB"
        assert prepared["verification"] == "not_configured"
        assert prepared["not_protected"] is True
        assert prepared.get("evidence") is None


def test_impact_and_behavior_endpoints_cannot_cross_project_ids(tmp_path: Path) -> None:
    first_root = repository(tmp_path, "first")
    second_root = repository(tmp_path, "second")
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        first_id = connect(client, first_root, "First")
        second_id = connect(client, second_root, "Second")
        (first_root / "src" / "formatTime.ts").write_text("export const changed = 1;\n")
        change = client.get(f"/projects/{first_id}/changes/current", headers=headers()).json()
        client.post(
            f"/projects/{first_id}/changes/{change['id']}/analyze", headers=headers(), json={}
        )
        assert (
            client.get(
                f"/projects/{second_id}/changes/{change['id']}", headers=headers()
            ).status_code
            == 404
        )
        assert (
            client.get(
                f"/projects/{second_id}/changes/{change['id']}/impact", headers=headers()
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/projects/{second_id}/changes/{change['id']}/context-receipt",
                headers=headers(),
                json={},
            ).status_code
            == 404
        )


def test_context_receipt_persists_no_source_or_sensitive_content_and_opens_no_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = repository(tmp_path)
    secret = "PHASE3-SECRET-MUST-NEVER-PERSIST-9B341"
    (root / ".env").write_text(f"TOKEN={secret}\n", encoding="utf-8")
    attempted: list[object] = []

    def deny_connect(_instance: object, address: object) -> None:
        attempted.append(address)
        raise AssertionError(f"network attempted: {address}")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    data = tmp_path / "data"
    with TestClient(create_app(EngineSettings(data_root=data, session_token=TOKEN))) as client:
        project_id = connect(client, root)
        (root / "src" / "formatTime.ts").write_text("export const changed = 1;\n")
        change = client.get(f"/projects/{project_id}/changes/current", headers=headers()).json()
        client.post(
            f"/projects/{project_id}/changes/{change['id']}/analyze", headers=headers(), json={}
        )
        receipt = client.post(
            f"/projects/{project_id}/changes/{change['id']}/context-receipt",
            headers=headers(),
            json={},
        ).json()
        clipboard_payload = json.dumps(receipt, sort_keys=True)
        assert secret not in clipboard_payload
        assert ".env" not in [item["relative_path"] for item in receipt["selected_files"]]
    assert attempted == []
    for path in data.rglob("*"):
        if path.is_file():
            assert secret.encode() not in path.read_bytes()
    with sqlite_rows(data / "database" / "mellowyak.sqlite3") as rows:
        assert not any(secret in value for value in rows)


class sqlite_rows:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.values: list[str] = []

    def __enter__(self) -> list[str]:
        import sqlite3

        self.connection = sqlite3.connect(self.path)
        for table in (
            "impact_analysis_inputs",
            "impact_analysis_results",
            "impact_analysis_paths",
            "context_receipts",
            "context_receipt_items",
        ):
            for row in self.connection.execute(f"SELECT * FROM {table}"):
                self.values.extend(str(value) for value in row if value is not None)
        return self.values

    def __exit__(self, *_args: object) -> None:
        self.connection.close()


def test_impact_explorer_returns_incoming_outgoing_provenance_and_staleness(tmp_path: Path) -> None:
    root = repository(tmp_path)
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    with TestClient(create_app(settings)) as client:
        project_id = connect(client, root)
        response = client.get(
            f"/projects/{project_id}/impact/search",
            headers=headers(),
            params={"query": "formatTime"},
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert results
        relationships = [relation for item in results for relation in item["relationships"]]
        assert any(item["direction"] == "incoming" for item in relationships)
        assert all(item["provenance"] and item["source_scan_revision"] for item in relationships)
        assert all("stale" in item for item in relationships)


def test_phase3_tables_never_store_source_content_columns(tmp_path: Path) -> None:
    settings = EngineSettings(data_root=tmp_path / "data", session_token=TOKEN)
    app = create_app(settings)
    with app.state.runtime.database.engine.connect() as connection:
        columns = {
            row[1]
            for table in (
                "impact_analyses",
                "impact_analysis_inputs",
                "impact_analysis_results",
                "impact_analysis_paths",
                "context_receipts",
                "context_receipt_items",
            )
            for row in connection.execute(text(f"PRAGMA table_info({table})"))
        }
    assert "source_content" not in columns
    assert "full_source" not in columns
    assert "snippet_content" not in columns


def test_medium_graph_analysis_is_bounded_and_fast() -> None:
    nodes = [NodeFact("changed", "FILE", "changed.ts", "src/changed.ts")]
    nodes.extend(
        NodeFact(f"consumer-{index}", "FILE", f"consumer-{index}.ts", f"src/consumer-{index}.ts")
        for index in range(1_000)
    )
    edges = [
        EdgeFact(
            f"edge-{index}",
            f"consumer-{index}",
            "changed",
            "IMPORTS",
            "STATIC_PARSED",
            "ecma",
            "scan-medium",
        )
        for index in range(1_000)
    ]
    started = time.perf_counter()
    outcome = traverse(nodes, edges, ["changed"], TraversalPolicy(max_result_nodes=250))
    elapsed = time.perf_counter() - started
    assert len(outcome.results) == 250
    assert outcome.truncated is True
    assert "maximum result nodes reached" in outcome.truncation_reasons
    assert elapsed < 2.0


@pytest.mark.parametrize("starting_revision", ["0001_local_core", "0002_project_git_impact"])
def test_phase3_migration_preserves_existing_project_rows(
    tmp_path: Path, starting_revision: str
) -> None:
    paths = StoragePaths.create(tmp_path / starting_revision)
    database = LocalDatabase(paths)
    database.migrate()
    database.engine.dispose()
    config = Config(str(_alembic_config_path()))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{paths.sqlite_file}")
    command.downgrade(config, starting_revision)
    project_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    import sqlite3

    with sqlite3.connect(paths.sqlite_file) as connection:
        connection.execute(
            "INSERT INTO projects (id, display_name, root_path, created_at) VALUES (?, ?, ?, ?)",
            (project_id, "Preserved Phase Project", str(tmp_path / "source"), now),
        )
    upgraded = LocalDatabase(paths)
    assert upgraded.migrate() == "0004_behavior_evidence_browser"
    with upgraded.engine.connect() as connection:
        row = connection.execute(
            text("SELECT display_name, root_path FROM projects WHERE id = :id"), {"id": project_id}
        ).one()
        assert tuple(row) == ("Preserved Phase Project", str(tmp_path / "source"))
        tables = {
            item[0]
            for item in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
    assert {"project_changes", "context_receipts", "behavior_candidates"}.issubset(tables)
