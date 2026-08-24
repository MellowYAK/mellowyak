from __future__ import annotations

import json
from http.server import SimpleHTTPRequestHandler
from pathlib import Path


class PulsePlanHandler(SimpleHTTPRequestHandler):
    """Serve the SPA routes and one deterministic local API endpoint."""

    fixture_root = Path(__file__).resolve().parent

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, directory=str(self.fixture_root), **kwargs)

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] in {
            "/",
            "/calendar",
            "/events/new",
            "/events/planning-sync",
            "/events/planning-sync/reschedule",
        }:
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/events/planning-sync/reschedule":
            self.send_error(404)
            return
        length = min(int(self.headers.get("Content-Length", "0")), 1024)
        try:
            body = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self.send_error(400)
            return
        if body != {"time": "14:00"}:
            self.send_error(422)
            return
        payload = b'{"event_id":"planning-sync","time":"14:00"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
