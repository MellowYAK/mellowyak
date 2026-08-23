from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable


def parent_is_alive(parent_pid: int | None) -> bool:
    if parent_pid is None:
        return True
    if parent_pid <= 1:
        return False
    try:
        os.kill(parent_pid, 0)
    except (OSError, ProcessLookupError, PermissionError):
        return False
    return True


def supervise_parent(
    parent_pid: int | None,
    request_shutdown: Callable[[], None],
    interval_seconds: float = 1.0,
) -> threading.Thread | None:
    if parent_pid is None:
        return None

    def monitor() -> None:
        while parent_is_alive(parent_pid):
            time.sleep(interval_seconds)
        request_shutdown()

    thread = threading.Thread(target=monitor, name="mellowyak-parent-watch", daemon=True)
    thread.start()
    return thread
