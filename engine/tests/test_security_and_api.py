from __future__ import annotations

import json
import socket
from pathlib import Path

from fastapi.testclient import TestClient

from mellowyak_engine.api.app import create_app
from mellowyak_engine.main import create_loopback_socket
from mellowyak_engine.settings.config import EngineSettings

TOKEN = "test-session-token-that-is-long-enough-1234567890"


def make_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(EngineSettings(data_root=tmp_path, session_token=TOKEN)))


def authorized() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_loopback_only_binding_and_dynamic_port() -> None:
    listener = create_loopback_socket("127.0.0.1")
    try:
        host, port = listener.getsockname()[:2]
        assert host == "127.0.0.1"
        assert int(port) > 0
    finally:
        listener.close()


def test_wildcard_binding_is_rejected() -> None:
    try:
        create_loopback_socket("0.0.0.0")
    except RuntimeError as error:
        assert str(error) == "MELLOWYAK_LOOPBACK_ONLY"
    else:
        raise AssertionError("The local engine accepted 0.0.0.0")


def test_handshake_is_minimal_and_does_not_expose_token(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.get("/handshake")
    assert response.status_code == 200
    assert response.json() == {
        "status": "running",
        "mode": "local",
        "authentication": "required",
    }
    assert TOKEN not in response.text


def test_missing_and_invalid_tokens_are_rejected(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_valid_token_and_first_setup_values(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    health = client.get("/health", headers=authorized())
    assert health.status_code == 200
    body = health.json()
    assert body["status"] == "ready"
    assert body["mode"] == "local"
    assert body["database_status"] == "ready"
    assert body["database_schema_version"] == "0009_technical_preview_readiness"
    assert body["cloud_connected"] is False
    assert body["outbound_network_enabled"] is False

    privacy = client.get("/settings/privacy", headers=authorized()).json()
    assert privacy == {
        "mode": "local",
        "cloud_connected": False,
        "outbound_network_enabled": False,
        "source_upload_enabled": False,
        "telemetry_upload_enabled": False,
        "account_required": False,
    }
    paths = client.get("/storage/paths", headers=authorized()).json()
    assert Path(paths["data_root"]) == tmp_path.resolve()
    assert Path(paths["evidence"]).is_dir()
    installation = client.get("/installation", headers=authorized()).json()
    assert installation["installation_id"]
    assert installation["database_schema_version"] == "0009_technical_preview_readiness"


def test_unapproved_origin_is_rejected(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.get(
        "/health", headers={**authorized(), "Origin": "https://untrusted.example"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "ORIGIN_NOT_ALLOWED"


def test_session_token_is_absent_from_logs(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.get("/health", headers=authorized())
    logs = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "logs").glob("*"))
    assert "engine_runtime_ready" in logs
    assert TOKEN not in logs
    assert str(tmp_path) not in logs


def test_startup_performs_no_outbound_network(monkeypatch, tmp_path: Path) -> None:
    attempted: list[object] = []
    original_connect = socket.socket.connect

    def deny_connect(instance, address):  # type: ignore[no-untyped-def]
        attempted.append(address)
        raise AssertionError(f"Outbound connection attempted: {address}")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    try:
        app = create_app(EngineSettings(data_root=tmp_path, session_token=TOKEN))
        assert app.state.runtime.schema_version == "0009_technical_preview_readiness"
        assert attempted == []
    finally:
        monkeypatch.setattr(socket.socket, "connect", original_connect)


def test_no_cloud_endpoint_or_analytics_dependency() -> None:
    root = Path(__file__).resolve().parents[2]
    source_roots = (
        root / "engine" / "src",
        root / "apps" / "desktop" / "src",
        root / "apps" / "desktop" / "src-tauri" / "src",
    )
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for source_root in source_roots
        for path in source_root.rglob("*")
        if path.suffix in {".py", ".rs", ".ts", ".tsx"}
    )
    forbidden = ("api.mellowyak", "cloud.mellowyak", "segment.io", "sentry.io", "analytics")
    assert not any(value in source.lower() for value in forbidden)
    assert "localstorage" not in source.lower()
    json.dumps({"checked": forbidden})
