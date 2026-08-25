from __future__ import annotations

import difflib

from mellowyak_engine.repair_candidates.manifest import MAX_DIFF_LINES, MAX_PREVIEW_BYTES


def bounded_unified_diff(
    before: bytes,
    after: bytes,
    *,
    before_name: str,
    after_name: str,
) -> dict[str, object]:
    if len(before) > MAX_PREVIEW_BYTES or len(after) > MAX_PREVIEW_BYTES:
        return {"available": False, "reason": "DIFF_PREVIEW_SIZE_LIMIT", "lines": []}
    if b"\0" in before or b"\0" in after:
        return {"available": False, "reason": "DIFF_BINARY_UNAVAILABLE", "lines": []}
    old = before.decode("utf-8", errors="replace").splitlines()
    new = after.decode("utf-8", errors="replace").splitlines()
    lines = list(
        difflib.unified_diff(old, new, fromfile=before_name, tofile=after_name, lineterm="")
    )
    truncated = len(lines) > MAX_DIFF_LINES
    return {
        "available": True,
        "reason": None,
        "lines": lines[:MAX_DIFF_LINES],
        "truncated": truncated,
    }
