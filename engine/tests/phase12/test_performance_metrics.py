from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from mellowyak_engine.api.app import create_app
from mellowyak_engine.db.models import DiagnosticRun
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "phase12-performance-session-token-that-is-long-enough"


def test_route_performance_metric_is_authenticated_bounded_and_durable(tmp_path: Path) -> None:
    app = create_app(
        EngineSettings(
            data_root=tmp_path / "data",
            session_token=TOKEN,
        )
    )
    with TestClient(app) as client:
        unauthorized = client.post(
            "/diagnostics/performance",
            json={"metric": "frontend_ready", "duration_ms": 12.5},
        )
        assert unauthorized.status_code == 401
        recorded = client.post(
            "/diagnostics/performance",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={
                "metric": "first_project_overview_data",
                "duration_ms": 42.75,
                "route": "project_overview",
                "project_id": "00000000-0000-0000-0000-000000000001",
            },
        )
        assert recorded.status_code == 200, recorded.text
        assert recorded.json()["status"] == "RECORDED"
        with app.state.runtime.database.sessions() as session:
            row = session.scalar(select(DiagnosticRun).where(DiagnosticRun.status == "PERFORMANCE"))
            assert row is not None
            summary = json.loads(row.summary_json)
            assert summary["metric"] == "first_project_overview_data"
            assert summary["duration_ms"] == 42.75

        invalid = client.post(
            "/diagnostics/performance",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"metric": "arbitrary_metric", "duration_ms": 1},
        )
        assert invalid.status_code == 400
