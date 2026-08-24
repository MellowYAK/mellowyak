from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

SUPPORTED_ASSERTIONS = frozenset(
    {
        "URL_EQUALS",
        "URL_CONTAINS",
        "ELEMENT_VISIBLE",
        "ELEMENT_HIDDEN",
        "TEXT_CONTAINS",
        "ATTRIBUTE_EQUALS",
        "API_CALL_OBSERVED",
        "HTTP_STATUS_OBSERVED",
    }
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def evaluate_assertion(
    page: Any, assertion: dict[str, Any], observations: list[dict[str, Any]], adapter_version: str
) -> dict[str, Any]:
    started = _now()
    kind = str(assertion.get("type", ""))
    expected = assertion.get("expected", assertion.get("value"))
    selector = str(assertion.get("selector", ""))
    observed: Any = None
    result = "PASS"
    failure: str | None = None
    try:
        if kind == "URL_EQUALS":
            observed = page.url
            result = "PASS" if observed == str(expected) else "FAIL"
        elif kind == "URL_CONTAINS":
            observed = page.url
            result = "PASS" if str(expected) in observed else "FAIL"
        elif kind in {"ELEMENT_VISIBLE", "ELEMENT_HIDDEN"}:
            if not selector:
                raise ValueError("ASSERTION_SELECTOR_REQUIRED")
            observed = page.locator(selector).is_visible(timeout=5000)
            target = kind == "ELEMENT_VISIBLE"
            result = "PASS" if observed is target else "FAIL"
        elif kind == "TEXT_CONTAINS":
            observed = (
                page.locator(selector).inner_text(timeout=5000)
                if selector
                else page.locator("body").inner_text(timeout=5000)
            )
            result = "PASS" if str(expected) in observed else "FAIL"
        elif kind == "ATTRIBUTE_EQUALS":
            if not selector or not assertion.get("attribute"):
                raise ValueError("ASSERTION_ATTRIBUTE_REQUIRED")
            observed = page.locator(selector).get_attribute(
                str(assertion["attribute"]), timeout=5000
            )
            result = "PASS" if observed == str(expected) else "FAIL"
        elif kind == "API_CALL_OBSERVED":
            method = str(assertion.get("method", "GET")).upper()
            observed = [
                item
                for item in observations
                if item.get("kind") == "request"
                and item.get("method") == method
                and str(expected) in str(item.get("url", ""))
            ]
            result = "PASS" if observed else "FAIL"
        elif kind == "HTTP_STATUS_OBSERVED":
            expected_status = int(assertion.get("status", expected))
            path = str(assertion.get("path", ""))
            observed = [
                item
                for item in observations
                if item.get("kind") == "response"
                and item.get("status") == expected_status
                and path in str(item.get("url", ""))
            ]
            result = "PASS" if observed else "FAIL"
        elif kind == "SCREENSHOT_REFERENCE":
            result = "NEEDS_REVIEW"
            observed = "HUMAN_VISUAL_REVIEW_REQUIRED"
        elif kind == "HUMAN_NOTE":
            result = "NEEDS_REVIEW"
            observed = "DOCUMENTATION_ONLY"
        else:
            result = "INCONCLUSIVE"
            failure = "ASSERTION_TYPE_UNSUPPORTED"
    except Exception as error:
        result = "INCONCLUSIVE"
        failure = "ASSERTION_TARGET_UNAVAILABLE"
        observed = type(error).__name__
    if result == "FAIL":
        failure = "EXPECTED_VALUE_NOT_OBSERVED"
    return {
        "assertion_type": kind,
        "expected": expected,
        "observed": observed,
        "result": result,
        "evidence_references": [],
        "failure_reason": failure,
        "adapter_version": adapter_version,
        "started_at": started,
        "completed_at": _now(),
    }
