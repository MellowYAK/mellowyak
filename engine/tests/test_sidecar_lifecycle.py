from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from mellowyak_engine.core.lifecycle import parent_is_alive, supervise_parent

TOKEN = "sidecar-test-token-that-is-long-enough-123456789"


def test_parent_supervision_requests_shutdown_when_parent_is_missing() -> None:
    shutdown = threading.Event()
    thread = supervise_parent(999_999_999, shutdown.set, interval_seconds=0.01)
    assert thread is not None
    thread.join(timeout=1)
    assert shutdown.is_set()


def test_parent_probe_recognizes_current_process() -> None:
    assert parent_is_alive(os.getpid()) is True


def test_real_sidecar_handshake_and_authenticated_health(tmp_path: Path) -> None:
    engine_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONPATH": str(engine_root / "src"),
            "MELLOWYAK_SESSION_TOKEN": TOKEN,
            "MELLOWYAK_DATA_ROOT": str(tmp_path),
            "MELLOWYAK_BIND_HOST": "127.0.0.1",
        }
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "mellowyak_engine.main"],
        cwd=engine_root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        handshake = json.loads(process.stdout.readline())
        assert handshake["schema"] == "mellowyak.sidecar.handshake.v1"
        assert handshake["host"] == "127.0.0.1"
        assert handshake["port"] > 0
        assert TOKEN not in json.dumps(handshake)
        request = Request(
            f"http://127.0.0.1:{handshake['port']}/health",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        with urlopen(request, timeout=5) as response:
            body = json.load(response)
        assert body["status"] == "ready"
        assert body["outbound_network_enabled"] is False
    finally:
        process.terminate()
        process.wait(timeout=5)
