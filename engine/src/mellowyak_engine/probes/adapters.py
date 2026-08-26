from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from threading import Event
from typing import Any, Protocol
from urllib.parse import urlsplit

from mellowyak_engine.runtime_adapters import SafeProcessRunner
from mellowyak_engine.verification.adapters.base import ReplayInput
from mellowyak_engine.verification.adapters.browser_replay import BrowserReplayAdapter

MAX_CAPTURE_BYTES = 32_768
MAX_REQUEST_BYTES = 32_768
MAX_TIMEOUT_SECONDS = 300
FORBIDDEN_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization", "x-api-key"})
SECRET_FIELD = re.compile(
    r"token|secret|password|passwd|cookie|authorization|credential|api[_-]?key", re.I
)
DENIED_SHELL_EXECUTABLES = frozenset(
    {
        "bash",
        "cmd",
        "cmd.exe",
        "csh",
        "dash",
        "fish",
        "nu",
        "powershell",
        "powershell.exe",
        "pwsh",
        "sh",
        "tcsh",
        "zsh",
    }
)


@dataclass(frozen=True)
class ProbeRequest:
    project_root: Path
    probe_type: str
    definition: dict[str, Any]
    expected: dict[str, Any] = field(default_factory=dict)
    evidence_policy: dict[str, Any] = field(default_factory=dict)
    source_identity: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30


@dataclass(frozen=True)
class ProbeExecution:
    result: str
    expected: dict[str, Any]
    observed: dict[str, Any]
    evidence: dict[str, Any]
    limitations: tuple[str, ...] = ()
    retryable: bool = False


class ProbeAdapter(Protocol):
    probe_type: str

    def run(self, request: ProbeRequest, cancelled: Event) -> ProbeExecution: ...


def _bounded_text(value: bytes | str) -> tuple[str, bool]:
    raw = value if isinstance(value, bytes) else value.encode("utf-8", errors="replace")
    clipped = raw[:MAX_CAPTURE_BYTES]
    return clipped.decode("utf-8", errors="replace"), len(raw) > len(clipped)


def _safe_executable(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("PROBE_EXECUTABLE_INVALID")
    if Path(value.strip()).name.casefold() in DENIED_SHELL_EXECUTABLES:
        raise ValueError("PROBE_SHELL_EXECUTABLE_DENIED")
    return value.strip()


def _output_evidence(
    stdout: bytes | str,
    stderr: bytes | str,
    *,
    stdout_truncated: bool,
    stderr_truncated: bool,
) -> dict[str, Any]:
    """Persist bounded metadata, never process output that may contain project secrets."""
    stdout_raw = stdout if isinstance(stdout, bytes) else stdout.encode("utf-8", errors="replace")
    stderr_raw = stderr if isinstance(stderr, bytes) else stderr.encode("utf-8", errors="replace")
    return {
        "stdout_bytes": len(stdout_raw),
        "stderr_bytes": len(stderr_raw),
        "stdout_sha256": hashlib.sha256(stdout_raw).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr_raw).hexdigest(),
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }


def _assert_text(text: str, expected: dict[str, Any]) -> tuple[bool, list[str]]:
    failures: list[str] = []
    contains = expected.get("contains")
    if isinstance(contains, str) and contains not in text:
        failures.append("TEXT_ASSERTION_FAILED")
    pattern = expected.get("regex")
    if isinstance(pattern, str):
        try:
            if re.search(pattern, text) is None:
                failures.append("REGEX_ASSERTION_FAILED")
        except re.error:
            failures.append("REGEX_INVALID")
    return not failures, failures


class CliProbeAdapter:
    probe_type = "CLI"

    def run(self, request: ProbeRequest, cancelled: Event) -> ProbeExecution:
        definition = request.definition
        executable = _safe_executable(definition.get("executable"))
        argv = definition.get("argv", [])
        if not isinstance(argv, list):
            raise ValueError("PROBE_ARGV_INVALID")
        if any(not isinstance(item, str) or "\x00" in item for item in argv):
            raise ValueError("PROBE_ARGV_INVALID")
        environment_names = definition.get("environment_names", [])
        if not isinstance(environment_names, list) or any(
            not isinstance(item, str) for item in environment_names
        ):
            raise ValueError("PROBE_ENVIRONMENT_NAMES_INVALID")
        relative_cwd = str(definition.get("cwd", "."))
        timeout = max(1, min(int(request.timeout_seconds), MAX_TIMEOUT_SECONDS))
        execution = SafeProcessRunner().run(
            executable=executable,
            argv=argv,
            project_root=request.project_root,
            relative_working_directory=relative_cwd,
            environment_names=environment_names,
            timeout_seconds=timeout,
            output_limit_bytes=MAX_CAPTURE_BYTES,
            cancellation_event=cancelled,
        )
        cwd = Path(execution.working_directory)
        expected_exit = int(request.expected.get("exit_code", 0))
        text_ok, failures = _assert_text(execution.stdout, request.expected)
        output_file = request.expected.get("output_file")
        if isinstance(output_file, str):
            try:
                output_path = (cwd / output_file).resolve(strict=False)
                output_path.relative_to(request.project_root.resolve(strict=True))
                if not output_path.is_file():
                    failures.append("OUTPUT_FILE_MISSING")
            except (OSError, ValueError):
                failures.append("OUTPUT_FILE_OUTSIDE_PROJECT")
        exit_ok = execution.exit_code == expected_exit
        if execution.cancelled:
            result = "CANCELLED"
        elif exit_ok and text_ok and not failures:
            result = "PASS"
        else:
            result = "FAIL"
        return ProbeExecution(
            result=result,
            expected={"exit_code": expected_exit, **request.expected},
            observed={
                "exit_code": execution.exit_code,
                "duration_ms": round(execution.duration_seconds * 1000, 3),
                "timed_out": execution.timed_out,
                "assertion_failures": failures,
            },
            evidence=_output_evidence(
                execution.stdout,
                execution.stderr,
                stdout_truncated=execution.stdout_truncated,
                stderr_truncated=execution.stderr_truncated,
            ),
            retryable=execution.timed_out or (execution.exit_code not in {0, expected_exit}),
        )


class TestRunnerProbeAdapter(CliProbeAdapter):
    probe_type = "TEST"


def _loopback_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _json_value(payload: Any, path: str) -> Any:
    current = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            raise KeyError(path)
        current = current[segment]
    return current


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            SECRET_FIELD.search(str(key)) or _contains_secret_field(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_secret_field(item) for item in value)
    return False


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


class HttpProbeAdapter:
    probe_type = "HTTP"

    def run(self, request: ProbeRequest, cancelled: Event) -> ProbeExecution:
        if cancelled.is_set():
            return ProbeExecution("CANCELLED", request.expected, {}, {})
        raw_url = request.definition.get("url")
        if not isinstance(raw_url, str):
            raise ValueError("PROBE_HTTP_URL_INVALID")
        parsed = urlsplit(raw_url)
        if parsed.scheme not in {"http", "https"} or not _loopback_host(parsed.hostname):
            raise ValueError("PROBE_HTTP_LOOPBACK_REQUIRED")
        if parsed.username or parsed.password or parsed.query:
            raise ValueError("PROBE_HTTP_SECRET_BEARING_URL_DENIED")
        method = str(request.definition.get("method", "GET")).upper()
        if method not in {"GET", "HEAD", "POST"}:
            raise ValueError("PROBE_HTTP_METHOD_DENIED")
        raw_headers = request.definition.get("headers", {})
        if not isinstance(raw_headers, dict) or any(
            str(name).lower() in FORBIDDEN_HEADERS for name in raw_headers
        ):
            raise ValueError("PROBE_HTTP_SECRET_HEADER_DENIED")
        headers = {str(name): str(value) for name, value in raw_headers.items()}
        body: bytes | None = None
        if method == "POST":
            payload = request.definition.get("json_body")
            if payload is None or _contains_secret_field(payload):
                raise ValueError("PROBE_HTTP_BODY_INVALID")
            try:
                body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            except (TypeError, ValueError) as error:
                raise ValueError("PROBE_HTTP_BODY_INVALID") from error
            if len(body) > MAX_REQUEST_BYTES:
                raise ValueError("PROBE_HTTP_BODY_TOO_LARGE")
            headers.setdefault("Content-Type", "application/json")
        timeout = max(1, min(int(request.timeout_seconds), MAX_TIMEOUT_SECONDS))
        started = time.monotonic()
        try:
            opener = urllib.request.build_opener(_NoRedirect)
            with opener.open(
                urllib.request.Request(raw_url, data=body, method=method, headers=headers),
                timeout=timeout,
            ) as response:
                status = int(response.status)
                body_raw = response.read(MAX_CAPTURE_BYTES + 1)
        except urllib.error.HTTPError as error:
            status = error.code
            body_raw = error.read(MAX_CAPTURE_BYTES + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            return ProbeExecution(
                "FAIL",
                request.expected,
                {
                    "error_code": type(error).__name__,
                    "duration_ms": round((time.monotonic() - started) * 1000, 3),
                },
                {},
                retryable=True,
            )
        body, truncated = _bounded_text(body_raw)
        failures: list[str] = []
        expected_status = int(request.expected.get("status", 200))
        if status != expected_status:
            failures.append("STATUS_ASSERTION_FAILED")
        text_ok, text_failures = _assert_text(body, request.expected)
        failures.extend(text_failures)
        json_path = request.expected.get("json_path")
        if isinstance(json_path, str):
            try:
                value = _json_value(json.loads(body), json_path)
                if "json_value" in request.expected and value != request.expected["json_value"]:
                    failures.append("JSON_ASSERTION_FAILED")
            except (ValueError, KeyError):
                failures.append("JSON_ASSERTION_FAILED")
        duration_ms = round((time.monotonic() - started) * 1000, 3)
        maximum = request.expected.get("max_duration_ms")
        if isinstance(maximum, (int, float)) and duration_ms > maximum:
            failures.append("DURATION_ASSERTION_FAILED")
        evidence: dict[str, Any] = {"response_bytes": len(body_raw), "truncated": truncated}
        if request.evidence_policy.get("capture_response_excerpt") is True:
            evidence["response_excerpt"] = body
        return ProbeExecution(
            "PASS" if not failures and text_ok else "FAIL",
            request.expected,
            {"status": status, "duration_ms": duration_ms, "assertion_failures": failures},
            evidence,
            retryable=status >= 500,
        )


class ProcessHealthProbeAdapter:
    probe_type = "PROCESS"

    def run(self, request: ProbeRequest, cancelled: Event) -> ProbeExecution:
        executable = _safe_executable(request.definition.get("executable"))
        argv = request.definition.get("argv", [])
        if not isinstance(argv, list) or any(
            not isinstance(item, str) or "\x00" in item for item in argv
        ):
            raise ValueError("PROBE_ARGV_INVALID")
        environment_names = request.definition.get("environment_names", [])
        if not isinstance(environment_names, list) or any(
            not isinstance(item, str) for item in environment_names
        ):
            raise ValueError("PROBE_ENVIRONMENT_NAMES_INVALID")
        managed, _resolved, _cwd = SafeProcessRunner().start(
            executable=executable,
            argv=argv,
            project_root=request.project_root,
            relative_working_directory=str(request.definition.get("cwd", ".")),
            environment_names=environment_names,
            output_limit_bytes=MAX_CAPTURE_BYTES,
        )
        process = managed.process
        started = time.monotonic()
        alive_seconds = max(0.1, min(float(request.expected.get("alive_seconds", 1.0)), 10.0))
        deadline = started + min(request.timeout_seconds, MAX_TIMEOUT_SECONDS)
        port = request.expected.get("port")
        port_open = port is None
        while process.poll() is None and time.monotonic() < deadline and not cancelled.wait(0.05):
            if isinstance(port, int):
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        port_open = True
                except OSError:
                    pass
            if time.monotonic() - started >= alive_seconds and port_open:
                break
        remained_alive = process.poll() is None and time.monotonic() - started >= alive_seconds
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        managed.wait_for_readers(timeout=2)
        stdout = managed.stdout_capture.text()
        stderr = managed.stderr_capture.text()
        passed = remained_alive and port_open and not cancelled.is_set()
        return ProbeExecution(
            "CANCELLED" if cancelled.is_set() else "PASS" if passed else "FAIL",
            request.expected,
            {
                "remained_alive": remained_alive,
                "port_open": port_open,
                "exit_code": process.returncode,
                "duration_ms": round((time.monotonic() - started) * 1000, 3),
            },
            _output_evidence(
                stdout,
                stderr,
                stdout_truncated=managed.stdout_capture.truncated,
                stderr_truncated=managed.stderr_capture.truncated,
            ),
            retryable=not passed,
        )


class ManualProbeAdapter:
    probe_type = "MANUAL"

    def run(self, request: ProbeRequest, cancelled: Event) -> ProbeExecution:
        confirmed = request.definition.get("confirmed") is True
        return ProbeExecution(
            "CANCELLED" if cancelled.is_set() else "PASS" if confirmed else "INCONCLUSIVE",
            {"explicit_human_attestation": True},
            {"confirmed": confirmed, "note_present": bool(request.definition.get("note"))},
            {},
            ("MANUAL_NOT_AUTOMATED",),
        )


class BrowserProbeAdapter:
    probe_type = "BROWSER"

    def __init__(self) -> None:
        self._replay = BrowserReplayAdapter()

    def run(self, request: ProbeRequest, cancelled: Event) -> ProbeExecution:
        definition = request.definition
        required = {
            "entry_url",
            "allowed_origin",
            "viewport",
            "locale",
            "timezone",
            "steps",
            "assertions",
            "behavior_version_id",
            "baseline_id",
        }
        if not required.issubset(definition):
            return ProbeExecution(
                "INCONCLUSIVE",
                request.expected,
                {"delegated_to": "EXISTING_BROWSER_REPLAY"},
                {},
                ("BROWSER_REPLAY_REQUIRES_ACCEPTED_CURRENT_BASELINE",),
            )
        try:
            execution = self._replay.execute(
                ReplayInput(
                    entry_url=str(definition["entry_url"]),
                    allowed_origin=str(definition["allowed_origin"]),
                    viewport=dict(definition["viewport"]),
                    locale=str(definition["locale"]),
                    timezone=str(definition["timezone"]),
                    steps=list(definition["steps"]),
                    assertions=list(definition["assertions"]),
                    source_identity=request.source_identity,
                    behavior_version_id=str(definition["behavior_version_id"]),
                    baseline_id=str(definition["baseline_id"]),
                ),
                cancelled,
            )
        except (TypeError, ValueError):
            return ProbeExecution(
                "INCONCLUSIVE",
                request.expected,
                {"delegated_to": "EXISTING_BROWSER_REPLAY"},
                {},
                ("BROWSER_REPLAY_DEFINITION_INVALID",),
            )
        result = {
            "AUTOMATED_PASS": "PASS",
            "FAIL": "FAIL",
            "CANCELLED": "CANCELLED",
        }.get(execution.result, "INCONCLUSIVE")
        artifacts = [
            {
                "type": artifact_type,
                "media_type": media_type,
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
            for artifact_type, content, media_type in execution.artifacts
        ]
        return ProbeExecution(
            result,
            request.expected,
            {
                "delegated_to": "EXISTING_BROWSER_REPLAY",
                "assertion_results": execution.assertion_results,
                "runtime_identity": execution.runtime_identity,
                "failure_reason": execution.failure_reason,
            },
            {"artifacts": artifacts},
            tuple(execution.limitations),
            retryable=result == "FAIL",
        )


def default_probe_registry() -> dict[str, ProbeAdapter]:
    adapters: list[ProbeAdapter] = [
        BrowserProbeAdapter(),
        HttpProbeAdapter(),
        CliProbeAdapter(),
        ProcessHealthProbeAdapter(),
        TestRunnerProbeAdapter(),
        ManualProbeAdapter(),
    ]
    return {adapter.probe_type: adapter for adapter in adapters}
