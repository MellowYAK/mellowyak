from __future__ import annotations

import json
import socket
import sys

import uvicorn

from mellowyak_engine.api.app import create_app
from mellowyak_engine.core.lifecycle import supervise_parent
from mellowyak_engine.settings.config import ALLOWED_HOSTS, EngineSettings


def create_loopback_socket(host: str) -> socket.socket:
    if host not in ALLOWED_HOSTS:
        raise RuntimeError("MELLOWYAK_LOOPBACK_ONLY")
    family = socket.AF_INET6 if host == "::1" else socket.AF_INET
    listener = socket.socket(family, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, 0))
    listener.listen(128)
    return listener


def main() -> None:
    settings = EngineSettings.from_environment()
    app = create_app(settings)
    listener = create_loopback_socket(settings.bind_host)
    port = int(listener.getsockname()[1])
    config = uvicorn.Config(
        app,
        host=settings.bind_host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    supervise_parent(settings.parent_pid, lambda: setattr(server, "should_exit", True))
    sys.stdout.write(
        json.dumps(
            {
                "schema": "mellowyak.sidecar.handshake.v1",
                "host": settings.bind_host,
                "port": port,
                "mode": "local",
            },
            separators=(",", ":"),
        )
        + "\n"
    )
    sys.stdout.flush()
    server.run(sockets=[listener])


if __name__ == "__main__":
    main()
