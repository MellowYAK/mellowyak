#!/usr/bin/env python3
"""Loopback-only HTTP/API/static service for the synthetic Acceptance Lab."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *arguments: object, **keywords: object) -> None:
        super().__init__(*arguments, directory=str(ROOT / "web"), **keywords)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._json({"mode": "local", "status": "ok"})
            return
        if self.path == "/api/checkout":
            behavior = json.loads((ROOT / "behavior.json").read_text())
            self._json(
                {
                    "currency": behavior["currency"],
                    "enabled": bool(behavior["checkout_enabled"]),
                }
            )
            return
        super().do_GET()

    def _json(self, value: object) -> None:
        payload = json.dumps(value, sort_keys=True).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format: str, *_arguments: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    arguments = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), Handler)
    print(json.dumps({"host": "127.0.0.1", "port": server.server_port}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
