from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event

import pytest

from mellowyak_engine.probes.adapters import HttpProbeAdapter, ProbeRequest


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        body = json.dumps({"driver": {"id": "driver-near"}, "pickup": payload["pickup"]}).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def test_http_probe_posts_bounded_json_and_checks_selected_value(tmp_path: Path) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = HttpProbeAdapter().run(
            ProbeRequest(
                project_root=tmp_path,
                probe_type="HTTP",
                definition={
                    "method": "POST",
                    "url": f"http://127.0.0.1:{server.server_port}/api/rides",
                    "json_body": {"pickup": [0, 0], "destination": [8, 8]},
                },
                expected={"status": 201, "json_path": "driver.id", "json_value": "driver-near"},
            ),
            Event(),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert result.result == "PASS"
    assert result.observed["status"] == 201
    assert "response_excerpt" not in result.evidence


@pytest.mark.parametrize(
    ("definition", "code"),
    [
        (
            {
                "method": "POST",
                "url": "http://127.0.0.1:7/api/rides",
                "json_body": {"api_token": "secret-canary"},
            },
            "PROBE_HTTP_BODY_INVALID",
        ),
        (
            {"method": "GET", "url": "https://example.com/api/rides"},
            "PROBE_HTTP_LOOPBACK_REQUIRED",
        ),
    ],
)
def test_http_probe_rejects_secret_bodies_and_external_origins(
    tmp_path: Path, definition: dict[str, object], code: str
) -> None:
    with pytest.raises(ValueError, match=code):
        HttpProbeAdapter().run(
            ProbeRequest(project_root=tmp_path, probe_type="HTTP", definition=definition),
            Event(),
        )
