from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationCheck:
    check_id: str
    check_type: str
    requirement: str
    path: str | None = None
    expected: str | None = None
    executable: str | None = None
    argv: tuple[str, ...] = ()
    cwd: str = "."
    expected_exit_code: int = 0
    stdout_contains: str | None = None


def checks_from_policy(value: dict[str, Any]) -> tuple[ValidationCheck, ...]:
    checks: list[ValidationCheck] = []
    for index, item in enumerate(value.get("checks", [])):
        if not isinstance(item, dict):
            continue
        checks.append(
            ValidationCheck(
                check_id=str(item.get("id") or f"check-{index + 1}"),
                check_type=str(item.get("type") or "MANUAL_REVIEW"),
                requirement=str(item.get("requirement") or "REQUIRED"),
                path=None if item.get("path") is None else str(item["path"]),
                expected=None if item.get("expected") is None else str(item["expected"]),
                executable=(None if item.get("executable") is None else str(item["executable"])),
                argv=tuple(str(value) for value in item.get("argv", []) if isinstance(value, str)),
                cwd=str(item.get("cwd") or "."),
                expected_exit_code=int(item.get("expected_exit_code", 0)),
                stdout_contains=(
                    None if item.get("stdout_contains") is None else str(item["stdout_contains"])
                ),
            )
        )
    if not checks:
        checks = [
            ValidationCheck("original-failed-probe", "ORIGINAL_FAILED_PROBE", "REQUIRED"),
            ValidationCheck("impacted-required-checks", "IMPACTED_PROBES", "REQUIRED"),
        ]
    return tuple(checks)
