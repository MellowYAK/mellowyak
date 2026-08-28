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
    if os.name == "nt":
        return _windows_process_is_alive(parent_pid)
    try:
        os.kill(parent_pid, 0)
    except (OSError, ProcessLookupError, PermissionError):
        return False
    return True


def _windows_process_is_alive(process_id: int) -> bool:
    import ctypes
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    still_active = 259
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(process_query_limited_information, False, process_id)
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and (
            exit_code.value == still_active
        )
    finally:
        kernel32.CloseHandle(handle)


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
