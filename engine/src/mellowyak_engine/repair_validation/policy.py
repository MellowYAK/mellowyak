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
            )
        )
    if not checks:
        checks = [
            ValidationCheck("original-failed-probe", "ORIGINAL_FAILED_PROBE", "REQUIRED"),
            ValidationCheck("impacted-required-checks", "IMPACTED_PROBES", "REQUIRED"),
        ]
    return tuple(checks)
