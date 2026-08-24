from __future__ import annotations

import json
import time
from threading import Event
from urllib.parse import urlsplit

from mellowyak_engine.behaviors.service import validate_loopback_runtime_url
from mellowyak_engine.browser.service import _browser_executable, _safe_url
from mellowyak_engine.verification.adapters.base import AdapterExecution, ReplayInput
from mellowyak_engine.verification.assertions import evaluate_assertion

BEHAVIOR_TIMEOUT_MS = 120_000


class BrowserReplayAdapter:
    name = "BROWSER_REPLAY"
    version = "browser-replay-v1"

    def availability(self) -> tuple[bool, str | None]:
        try:
            import playwright.sync_api  # noqa: F401
        except Exception:
            return False, "PLAYWRIGHT_UNAVAILABLE"
        if not _browser_executable():
            return False, "CHROMIUM_UNAVAILABLE"
        return True, None

    def execute(self, request: ReplayInput, cancel: Event) -> AdapterExecution:
        available, reason = self.availability()
        if not available:
            return AdapterExecution(result="INCONCLUSIVE", failure_reason=reason)
        normalized, origin = validate_loopback_runtime_url(request.entry_url)
        if origin != request.allowed_origin:
            return AdapterExecution(result="INCONCLUSIVE", failure_reason="RUNTIME_ORIGIN_CHANGED")
        from playwright.sync_api import sync_playwright

        started = time.monotonic()
        observations: list[dict[str, object]] = []
        action_log: list[dict[str, object]] = []
        browser = context = None
        try:
            runtime = sync_playwright().start()
            browser = runtime.chromium.launch(
                headless=True,
                executable_path=_browser_executable(),
                args=["--disable-background-networking", "--disable-sync"],
            )
            context = browser.new_context(
                accept_downloads=False,
                service_workers="block",
                viewport=request.viewport,
                locale=request.locale,
                timezone_id=request.timezone,
            )

            def route_guard(route, browser_request):  # type: ignore[no-untyped-def]
                parsed = urlsplit(browser_request.url)
                request_origin = (
                    f"{parsed.scheme}://{parsed.hostname}:{parsed.port}" if parsed.port else ""
                )
                if request_origin == request.allowed_origin and parsed.scheme == "http":
                    route.continue_()
                else:
                    route.abort("blockedbyclient")

            context.route("**/*", route_guard)
            page = context.new_page()
            page.on(
                "request",
                lambda item: observations.append(
                    {
                        "kind": "request",
                        "method": item.method,
                        "url": _safe_url(item.url),
                        "resource_type": item.resource_type,
                    }
                ),
            )
            page.on(
                "response",
                lambda item: observations.append(
                    {"kind": "response", "status": item.status, "url": _safe_url(item.url)}
                ),
            )
            page.goto(normalized, wait_until="domcontentloaded", timeout=30_000)
            for step in request.steps:
                if cancel.is_set():
                    return AdapterExecution(
                        result="CANCELLED", failure_reason="VERIFICATION_CANCELLED"
                    )
                if (time.monotonic() - started) * 1000 > BEHAVIOR_TIMEOUT_MS:
                    return AdapterExecution(result="ERROR", failure_reason="VERIFICATION_TIMEOUT")
                if not step.get("included", True):
                    continue
                event_type = str(step.get("event_type", ""))
                selector = str(step.get("selector") or "")
                metadata = dict(step.get("metadata") or {})
                if event_type == "change":
                    selected_index = metadata.get("selected_index")
                    if metadata.get("tag") == "SELECT" and isinstance(selected_index, int):
                        page.locator(selector).select_option(index=selected_index, timeout=20_000)
                    else:
                        return AdapterExecution(
                            result="INCONCLUSIVE", failure_reason="REPLAY_VALUE_NOT_RECORDED"
                        )
                elif event_type == "click":
                    page.locator(selector).click(timeout=20_000)
                elif event_type == "submit":
                    continue
                else:
                    return AdapterExecution(
                        result="INCONCLUSIVE", failure_reason="REPLAY_ACTION_UNSUPPORTED"
                    )
                action_log.append(
                    {
                        "event_type": event_type,
                        "selector": selector,
                        "page_url": _safe_url(page.url),
                    }
                )
            assertion_results = [
                evaluate_assertion(page, assertion, observations, self.version)
                for assertion in request.assertions[:100]
            ]
            page.evaluate(
                """() => document
                  .querySelectorAll('input,textarea,[contenteditable=true]')
                  .forEach(el => el.style.filter='blur(10px)')"""
            )
            screenshot = page.screenshot(type="png", full_page=False)
            if any(item["result"] == "FAIL" for item in assertion_results):
                result = "FAIL"
            elif any(
                item["result"] in {"INCONCLUSIVE", "NEEDS_REVIEW"} for item in assertion_results
            ):
                result = "NEEDS_REVIEW"
            elif not assertion_results:
                result = "INCONCLUSIVE"
            else:
                result = "AUTOMATED_PASS"
            return AdapterExecution(
                result=result,
                assertion_results=assertion_results,
                artifacts=[
                    ("CURRENT_SCREENSHOT", screenshot, "image/png"),
                    (
                        "CURRENT_ACTIONS",
                        json.dumps(action_log, sort_keys=True).encode(),
                        "application/json",
                    ),
                    (
                        "CURRENT_NETWORK",
                        json.dumps(observations[:1000], sort_keys=True).encode(),
                        "application/json",
                    ),
                    (
                        "ASSERTION_RESULTS",
                        json.dumps(assertion_results, sort_keys=True).encode(),
                        "application/json",
                    ),
                ],
                runtime_identity={
                    "origin": request.allowed_origin,
                    "browser_version": browser.version,
                    "adapter": self.version,
                },
                limitations=["Ephemeral context; no baseline cookies or browser storage reused."],
                failure_reason="DETERMINISTIC_ASSERTION_FAILED" if result == "FAIL" else None,
            )
        except Exception as error:
            name = type(error).__name__
            if "Timeout" in name or "strict mode" in str(error).lower():
                return AdapterExecution(
                    result="INCONCLUSIVE", failure_reason="REPLAY_SELECTOR_UNRESOLVED"
                )
            return AdapterExecution(result="ERROR", failure_reason="BROWSER_REPLAY_ERROR")
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
            if "runtime" in locals():
                try:
                    runtime.stop()
                except Exception:
                    pass
