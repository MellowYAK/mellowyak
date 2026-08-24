from __future__ import annotations

from pathlib import Path


def apply(project_root: Path) -> None:
    target = project_root / "time-format.js"
    target.write_text(
        "export function formatEventTime(time) {\n"
        "  return `${time} IDT`;\n"
        "}\n"
        "export const savedTimeOffsetHours = 1;\n",
        encoding="utf-8",
    )
