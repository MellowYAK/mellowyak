from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from threading import Event
from typing import Any, Protocol

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_STOP_TIMEOUT_SECONDS = 3.0
DEFAULT_OUTPUT_LIMIT_BYTES = 64 * 1024
MAX_TIMEOUT_SECONDS = 300.0
MAX_OUTPUT_LIMIT_BYTES = 1024 * 1024
MAX_ARGV_ITEMS = 128
MAX_ARGUMENT_BYTES = 32 * 1024
MAX_SANITIZED_STRING_LENGTH = 4096

_BASE_ENVIRONMENT_NAMES = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "TMPDIR",
    "TEMP",
    "TMP",
    "LANG",
    "LC_ALL",
)
_SENSITIVE_ENVIRONMENT_NAME = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASSWD|AUTH|COOKIE|PRIVATE|CREDENTIAL|API_?KEY|SESSION)",
    re.IGNORECASE,
)
_DENIED_SHELL_EXECUTABLES = frozenset(
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


class DetectionConfidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OperationStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    UNAPPROVED = "UNAPPROVED"


class RuntimeState(StrEnum):
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    EXITED = "EXITED"
    STOPPED = "STOPPED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RuntimeDetection:
    runtime_type: str
    adapter_name: str
    adapter_version: str
    confidence: DetectionConfidence
    markers: tuple[str, ...]
    executable: str | None
    version: str | None
    reasons: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeDescription:
    runtime_type: str
    adapter_name: str
    adapter_version: str
    execution_supported: bool
    capabilities: tuple[str, ...]
    detections: tuple[RuntimeDetection, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeProfileSpec:
    profile_id: str
    project_root: Path
    runtime_type: str
    executable: str
    argv: tuple[str, ...] = ()
    relative_working_directory: str = "."
    approved: bool = False
    execution_mode: str = "MANAGED"
    environment_names: tuple[str, ...] = ()
    expected_ports: tuple[int, ...] = ()
    health_url: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    stop_timeout_seconds: float = DEFAULT_STOP_TIMEOUT_SECONDS
    output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES
    network_policy: str = "LOOPBACK_ONLY"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RuntimeValidation:
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    resolved_executable: str | None = None
    resolved_working_directory: str | None = None


@dataclass(frozen=True)
class RuntimeAvailability:
    available: bool
    status: OperationStatus
    executable: str | None = None
    version: str | None = None
    reason: str | None = None


@dataclass
class RuntimeInstance:
    instance_id: str
    profile_id: str
    runtime_type: str
    executable: str
    argv: tuple[str, ...]
    working_directory: str
    pid: int
    started_monotonic: float
    stop_timeout_seconds: float = DEFAULT_STOP_TIMEOUT_SECONDS
    correlation_id: str | None = None
    _managed_process: ManagedProcess | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class RuntimeStartResult:
    status: OperationStatus
    instance: RuntimeInstance | None = None
    reason: str | None = None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeObservation:
    status: OperationStatus
    state: RuntimeState
    running: bool
    exit_code: int | None
    uptime_seconds: float
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    correlation_id: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class RuntimeProbeSpec:
    probe_id: str
    kind: str = "COMMAND"
    executable: str | None = None
    argv: tuple[str, ...] = ()
    relative_working_directory: str | None = None
    approved: bool = False
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES
    expected_exit_code: int = 0
    stdout_contains: str | None = None
    stderr_contains: str | None = None
    cancellation_event: Event | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class RuntimeProbeResult:
    status: OperationStatus
    exit_code: int | None = None
    duration_seconds: float = 0.0
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False
    assertions: Mapping[str, bool] = field(default_factory=dict)
    reason: str | None = None
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeStopResult:
    status: OperationStatus
    exit_code: int | None = None
    reason: str | None = None


class RuntimeAdapter(Protocol):
    name: str
    version: str
    runtime_type: str

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]: ...

    def describe(self, project: Path) -> RuntimeDescription: ...

    def validate(self, profile: RuntimeProfileSpec) -> RuntimeValidation: ...

    def availability(self, profile: RuntimeProfileSpec) -> RuntimeAvailability: ...

    def start(
        self, profile: RuntimeProfileSpec, correlation_id: str | None = None
    ) -> RuntimeStartResult: ...

    def observe(self, profile: RuntimeProfileSpec, correlation_id: str) -> RuntimeObservation: ...

    def run_probe(
        self, profile: RuntimeProfileSpec, probe: RuntimeProbeSpec
    ) -> RuntimeProbeResult: ...

    def stop(self, instance: RuntimeInstance) -> RuntimeStopResult: ...

    def fingerprint(self, profile: RuntimeProfileSpec) -> str: ...

    def sanitize(self, event: Mapping[str, Any]) -> dict[str, Any]: ...

    def cleanup(self, instance: RuntimeInstance) -> RuntimeStopResult: ...


class _BoundedCapture:
    def __init__(self, limit_bytes: int) -> None:
        self._limit = max(1, min(int(limit_bytes), MAX_OUTPUT_LIMIT_BYTES))
        self._head_limit = self._limit // 2
        self._tail_limit = self._limit - self._head_limit
        self._head = bytearray()
        self._tail = bytearray()
        self._total = 0
        self._lock = threading.Lock()

    def append(self, chunk: bytes) -> None:
        if not chunk:
            return
        with self._lock:
            self._total += len(chunk)
            if len(self._head) < self._head_limit:
                take = min(len(chunk), self._head_limit - len(self._head))
                self._head.extend(chunk[:take])
                chunk = chunk[take:]
            if chunk and self._tail_limit:
                self._tail.extend(chunk)
                if len(self._tail) > self._tail_limit:
                    del self._tail[: len(self._tail) - self._tail_limit]

    @property
    def truncated(self) -> bool:
        with self._lock:
            return self._total > self._limit

    def text(self) -> str:
        with self._lock:
            if self._total <= self._limit:
                raw = bytes(self._head + self._tail)
            else:
                marker = b"\n...[output truncated]...\n"
                if self._limit <= len(marker):
                    raw = marker[: self._limit]
                else:
                    budget = self._limit - len(marker)
                    head_size = min(len(self._head), budget // 2)
                    tail_size = min(len(self._tail), budget - head_size)
                    tail = bytes(self._tail[-tail_size:]) if tail_size else b""
                    raw = bytes(self._head[:head_size]) + marker + tail
        return raw.decode("utf-8", errors="replace")


@dataclass
class ManagedProcess:
    process: subprocess.Popen[bytes]
    stdout_capture: _BoundedCapture
    stderr_capture: _BoundedCapture
    stdout_thread: threading.Thread
    stderr_thread: threading.Thread
    started_monotonic: float

    def wait_for_readers(self, timeout: float = 1.0) -> None:
        self.stdout_thread.join(timeout=timeout)
        self.stderr_thread.join(timeout=timeout)


class SafeProcessRunner:
    """Starts approved argv without a shell and drains output into bounded buffers."""

    def start(
        self,
        *,
        executable: str,
        argv: Sequence[str],
        project_root: Path,
        relative_working_directory: str,
        environment_names: Sequence[str] = (),
        output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES,
    ) -> tuple[ManagedProcess, str, Path]:
        root = project_root.expanduser().resolve(strict=True)
        cwd = resolve_working_directory(root, relative_working_directory)
        arguments = validate_argv(argv)
        environment = minimal_environment(environment_names)
        resolved_executable = resolve_executable(executable, cwd, environment.get("PATH"))
        popen_kwargs: dict[str, Any] = {}
        if os.name == "nt":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(
            [resolved_executable, *arguments],
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            **popen_kwargs,
        )
        stdout_capture = _BoundedCapture(output_limit_bytes)
        stderr_capture = _BoundedCapture(output_limit_bytes)
        stdout_thread = _reader_thread(process.stdout, stdout_capture, "runtime-stdout")
        stderr_thread = _reader_thread(process.stderr, stderr_capture, "runtime-stderr")
        managed = ManagedProcess(
            process=process,
            stdout_capture=stdout_capture,
            stderr_capture=stderr_capture,
            stdout_thread=stdout_thread,
            stderr_thread=stderr_thread,
            started_monotonic=time.monotonic(),
        )
        return managed, resolved_executable, cwd

    def run(
        self,
        *,
        executable: str,
        argv: Sequence[str],
        project_root: Path,
        relative_working_directory: str,
        environment_names: Sequence[str] = (),
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES,
        cancellation_event: Event | None = None,
    ) -> ProcessExecution:
        timeout = bounded_timeout(timeout_seconds)
        started = time.monotonic()
        managed, resolved, cwd = self.start(
            executable=executable,
            argv=argv,
            project_root=project_root,
            relative_working_directory=relative_working_directory,
            environment_names=environment_names,
            output_limit_bytes=output_limit_bytes,
        )
        timed_out = False
        cancelled = False
        while managed.process.poll() is None:
            if cancellation_event is not None and cancellation_event.is_set():
                cancelled = True
                _terminate_process(managed.process, DEFAULT_STOP_TIMEOUT_SECONDS)
                break
            if time.monotonic() - started >= timeout:
                timed_out = True
                _terminate_process(managed.process, DEFAULT_STOP_TIMEOUT_SECONDS)
                break
            time.sleep(0.02)
        exit_code = managed.process.wait(timeout=DEFAULT_STOP_TIMEOUT_SECONDS)
        managed.wait_for_readers()
        return ProcessExecution(
            executable=resolved,
            argv=tuple(validate_argv(argv)),
            working_directory=str(cwd),
            exit_code=exit_code,
            duration_seconds=max(0.0, time.monotonic() - started),
            stdout=managed.stdout_capture.text(),
            stderr=managed.stderr_capture.text(),
            stdout_truncated=managed.stdout_capture.truncated,
            stderr_truncated=managed.stderr_capture.truncated,
            timed_out=timed_out,
            cancelled=cancelled,
        )


@dataclass(frozen=True)
class ProcessExecution:
    executable: str
    argv: tuple[str, ...]
    working_directory: str
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    timed_out: bool
    cancelled: bool


class BaseRuntimeAdapter:
    name = "base"
    version = "1"
    runtime_type = "GENERIC"
    execution_supported = True
    capabilities = (
        "runtime.capability.detect",
        "runtime.capability.validate",
        "runtime.capability.start",
        "runtime.capability.observe",
        "runtime.capability.command_probe",
        "runtime.capability.stop",
    )

    def __init__(self, runner: SafeProcessRunner | None = None) -> None:
        self.runner = runner or SafeProcessRunner()
        self._instances: dict[str, RuntimeInstance] = {}

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        del project
        return ()

    def describe(self, project: Path) -> RuntimeDescription:
        detections = self.detect(project)
        limitations = tuple(
            dict.fromkeys(item for detection in detections for item in detection.limitations)
        )
        if not self.execution_supported:
            limitations = (*limitations, "runtime.limitations.execution_not_supported")
        return RuntimeDescription(
            runtime_type=self.runtime_type,
            adapter_name=self.name,
            adapter_version=self.version,
            execution_supported=self.execution_supported,
            capabilities=self.capabilities,
            detections=detections,
            limitations=tuple(dict.fromkeys(limitations)),
        )

    def validate(self, profile: RuntimeProfileSpec) -> RuntimeValidation:
        errors: list[str] = []
        warnings: list[str] = []
        resolved_cwd: Path | None = None
        resolved_executable: str | None = None
        try:
            root = profile.project_root.expanduser().resolve(strict=True)
            if not root.is_dir():
                errors.append("runtime.validation.project_root_not_directory")
            else:
                resolved_cwd = resolve_working_directory(root, profile.relative_working_directory)
        except (FileNotFoundError, NotADirectoryError, OSError, ValueError):
            errors.append("runtime.validation.invalid_working_directory")
        try:
            validate_argv(profile.argv)
        except ValueError:
            errors.append("runtime.validation.invalid_argv")
        if not 0 < profile.timeout_seconds <= MAX_TIMEOUT_SECONDS:
            errors.append("runtime.validation.invalid_timeout")
        if not 0 < profile.stop_timeout_seconds <= MAX_TIMEOUT_SECONDS:
            errors.append("runtime.validation.invalid_stop_timeout")
        if not 0 < profile.output_limit_bytes <= MAX_OUTPUT_LIMIT_BYTES:
            errors.append("runtime.validation.invalid_output_limit")
        if any(port < 1 or port > 65535 for port in profile.expected_ports):
            errors.append("runtime.validation.invalid_expected_port")
        unsafe_names = tuple(
            name for name in profile.environment_names if not is_safe_environment_name(name)
        )
        if unsafe_names:
            errors.append("runtime.validation.unsafe_environment_name")
        if not profile.approved:
            warnings.append("runtime.validation.execution_not_approved")
        if not self.execution_supported:
            warnings.append("runtime.validation.execution_not_supported")
        if resolved_cwd is not None and profile.executable:
            try:
                path_value = minimal_environment(profile.environment_names).get("PATH")
                resolved_executable = resolve_executable(
                    profile.executable, resolved_cwd, path_value
                )
            except ValueError as error:
                code = str(error)
                errors.append(
                    code
                    if code.startswith("runtime.validation.")
                    else "runtime.validation.executable_unavailable"
                )
            except (FileNotFoundError, OSError):
                errors.append("runtime.validation.executable_unavailable")
        elif not profile.executable:
            errors.append("runtime.validation.executable_required")
        return RuntimeValidation(
            valid=not errors,
            errors=tuple(dict.fromkeys(errors)),
            warnings=tuple(dict.fromkeys(warnings)),
            resolved_executable=resolved_executable,
            resolved_working_directory=str(resolved_cwd) if resolved_cwd else None,
        )

    def availability(self, profile: RuntimeProfileSpec) -> RuntimeAvailability:
        if not self.execution_supported:
            return RuntimeAvailability(
                available=False,
                status=OperationStatus.UNSUPPORTED,
                reason="runtime.availability.execution_not_supported",
            )
        validation = self.validate(profile)
        if not validation.valid:
            return RuntimeAvailability(
                available=False,
                status=OperationStatus.UNAVAILABLE,
                reason=validation.errors[0],
            )
        return RuntimeAvailability(
            available=True,
            status=OperationStatus.SUCCEEDED,
            executable=validation.resolved_executable,
            version=self.executable_version(profile),
        )

    def executable_version(self, profile: RuntimeProfileSpec) -> str | None:
        del profile
        return None

    def start(
        self, profile: RuntimeProfileSpec, correlation_id: str | None = None
    ) -> RuntimeStartResult:
        if not self.execution_supported:
            return RuntimeStartResult(
                status=OperationStatus.UNSUPPORTED,
                reason="runtime.start.execution_not_supported",
            )
        if not profile.approved:
            return RuntimeStartResult(
                status=OperationStatus.UNAPPROVED,
                reason="runtime.start.approval_required",
            )
        if profile.execution_mode.upper() != "MANAGED":
            return RuntimeStartResult(
                status=OperationStatus.UNSUPPORTED,
                reason="runtime.start.managed_mode_required",
            )
        current = self._instances.get(profile.profile_id)
        if (
            current is not None
            and current._managed_process is not None
            and current._managed_process.process.poll() is None
        ):
            return RuntimeStartResult(
                status=OperationStatus.FAILED,
                reason="runtime.start.profile_already_running",
            )
        validation = self.validate(profile)
        if not validation.valid:
            return RuntimeStartResult(
                status=OperationStatus.FAILED,
                reason=validation.errors[0],
            )
        try:
            managed, executable, cwd = self.runner.start(
                executable=profile.executable,
                argv=profile.argv,
                project_root=profile.project_root,
                relative_working_directory=profile.relative_working_directory,
                environment_names=profile.environment_names,
                output_limit_bytes=profile.output_limit_bytes,
            )
        except (FileNotFoundError, OSError, ValueError, subprocess.SubprocessError):
            return RuntimeStartResult(
                status=OperationStatus.FAILED,
                reason="runtime.start.process_start_failed",
            )
        instance = RuntimeInstance(
            instance_id=str(uuid.uuid4()),
            profile_id=profile.profile_id,
            runtime_type=profile.runtime_type,
            executable=executable,
            argv=tuple(profile.argv),
            working_directory=str(cwd),
            pid=managed.process.pid,
            started_monotonic=managed.started_monotonic,
            stop_timeout_seconds=max(0.1, min(profile.stop_timeout_seconds, MAX_TIMEOUT_SECONDS)),
            correlation_id=correlation_id,
            _managed_process=managed,
        )
        self._instances[profile.profile_id] = instance
        return RuntimeStartResult(status=OperationStatus.SUCCEEDED, instance=instance)

    def observe(self, profile: RuntimeProfileSpec, correlation_id: str) -> RuntimeObservation:
        instance = self._instances.get(profile.profile_id)
        if instance is None:
            return RuntimeObservation(
                status=OperationStatus.UNAVAILABLE,
                state=RuntimeState.UNKNOWN,
                running=False,
                exit_code=None,
                uptime_seconds=0.0,
                correlation_id=correlation_id,
                reason="runtime.observe.instance_not_found",
            )
        return self.observe_instance(profile, instance, correlation_id)

    def observe_instance(
        self, profile: RuntimeProfileSpec, instance: RuntimeInstance, correlation_id: str
    ) -> RuntimeObservation:
        del profile
        managed = instance._managed_process
        if managed is None:
            return RuntimeObservation(
                status=OperationStatus.UNAVAILABLE,
                state=RuntimeState.UNKNOWN,
                running=False,
                exit_code=None,
                uptime_seconds=0.0,
                correlation_id=correlation_id,
                reason="runtime.observe.instance_not_managed",
            )
        exit_code = managed.process.poll()
        running = exit_code is None
        if not running:
            managed.wait_for_readers()
        return RuntimeObservation(
            status=OperationStatus.SUCCEEDED,
            state=RuntimeState.RUNNING if running else RuntimeState.EXITED,
            running=running,
            exit_code=exit_code,
            uptime_seconds=max(0.0, time.monotonic() - managed.started_monotonic),
            stdout=managed.stdout_capture.text(),
            stderr=managed.stderr_capture.text(),
            stdout_truncated=managed.stdout_capture.truncated,
            stderr_truncated=managed.stderr_capture.truncated,
            correlation_id=correlation_id,
        )

    def run_probe(self, profile: RuntimeProfileSpec, probe: RuntimeProbeSpec) -> RuntimeProbeResult:
        if not self.execution_supported:
            return RuntimeProbeResult(
                status=OperationStatus.UNSUPPORTED,
                reason="runtime.probe.execution_not_supported",
            )
        if not probe.approved:
            return RuntimeProbeResult(
                status=OperationStatus.UNAPPROVED,
                reason="runtime.probe.approval_required",
            )
        if probe.kind.upper() not in {"COMMAND", "CLI", "TEST", "TEST_RUNNER"}:
            return RuntimeProbeResult(
                status=OperationStatus.UNSUPPORTED,
                reason="runtime.probe.kind_not_supported_by_adapter",
            )
        executable = probe.executable or profile.executable
        argv = probe.argv or profile.argv
        cwd = probe.relative_working_directory or profile.relative_working_directory
        try:
            execution = self.runner.run(
                executable=executable,
                argv=argv,
                project_root=profile.project_root,
                relative_working_directory=cwd,
                environment_names=profile.environment_names,
                timeout_seconds=probe.timeout_seconds,
                output_limit_bytes=probe.output_limit_bytes,
                cancellation_event=probe.cancellation_event,
            )
        except (FileNotFoundError, OSError, ValueError, subprocess.SubprocessError):
            return RuntimeProbeResult(
                status=OperationStatus.FAILED,
                reason="runtime.probe.process_start_failed",
            )
        assertions = {
            "exit_code": execution.exit_code == probe.expected_exit_code,
        }
        if probe.stdout_contains is not None:
            assertions["stdout_contains"] = probe.stdout_contains in execution.stdout
        if probe.stderr_contains is not None:
            assertions["stderr_contains"] = probe.stderr_contains in execution.stderr
        if execution.cancelled:
            status = OperationStatus.CANCELLED
            reason = "runtime.probe.cancelled"
        elif execution.timed_out:
            status = OperationStatus.FAILED
            reason = "runtime.probe.timeout"
        elif all(assertions.values()):
            status = OperationStatus.SUCCEEDED
            reason = None
        else:
            status = OperationStatus.FAILED
            reason = "runtime.probe.assertion_failed"
        return RuntimeProbeResult(
            status=status,
            exit_code=execution.exit_code,
            duration_seconds=execution.duration_seconds,
            stdout=execution.stdout,
            stderr=execution.stderr,
            stdout_truncated=execution.stdout_truncated,
            stderr_truncated=execution.stderr_truncated,
            assertions=assertions,
            reason=reason,
        )

    def stop(self, instance: RuntimeInstance) -> RuntimeStopResult:
        managed = instance._managed_process
        if managed is None:
            return RuntimeStopResult(
                status=OperationStatus.UNAVAILABLE,
                reason="runtime.stop.instance_not_managed",
            )
        try:
            exit_code = _terminate_process(managed.process, instance.stop_timeout_seconds)
            managed.wait_for_readers()
        except (OSError, subprocess.SubprocessError):
            return RuntimeStopResult(
                status=OperationStatus.FAILED,
                reason="runtime.stop.process_stop_failed",
            )
        current = self._instances.get(instance.profile_id)
        if current is instance:
            self._instances.pop(instance.profile_id, None)
        return RuntimeStopResult(status=OperationStatus.SUCCEEDED, exit_code=exit_code)

    def fingerprint(self, profile: RuntimeProfileSpec) -> str:
        payload = {
            "adapter": self.name,
            "adapter_version": self.version,
            "runtime_type": profile.runtime_type,
            "executable": profile.executable,
            "argv": list(profile.argv),
            "working_directory": profile.relative_working_directory,
            "expected_ports": list(profile.expected_ports),
            "health_url": profile.health_url,
            "network_policy": profile.network_policy,
            "metadata": sanitize_value(profile.metadata),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def sanitize(self, event: Mapping[str, Any]) -> dict[str, Any]:
        return {str(key): sanitize_value(value, key=str(key)) for key, value in event.items()}

    def cleanup(self, instance: RuntimeInstance) -> RuntimeStopResult:
        return self.stop(instance)


def resolve_working_directory(project_root: Path, relative_working_directory: str) -> Path:
    root = project_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    relative = Path(relative_working_directory or ".")
    if relative.is_absolute():
        raise ValueError("runtime.validation.working_directory_must_be_relative")
    resolved = (root / relative).resolve(strict=True)
    if not resolved.is_dir():
        raise NotADirectoryError(resolved)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("runtime.validation.working_directory_outside_project") from error
    return resolved


def resolve_executable(executable: str, cwd: Path, path_value: str | None = None) -> str:
    value = executable.strip()
    if not value or "\x00" in value:
        raise ValueError("runtime.validation.invalid_executable")
    candidate = Path(value).expanduser()
    if candidate.name.casefold() in _DENIED_SHELL_EXECUTABLES:
        raise ValueError("runtime.validation.shell_executable_denied")
    has_path_separator = any(separator and separator in value for separator in (os.sep, os.altsep))
    if candidate.is_absolute() or has_path_separator:
        if not candidate.is_absolute():
            candidate = cwd / candidate
        resolved = candidate.resolve(strict=True)
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            raise FileNotFoundError(value)
        # Preserve a selected venv/shim path; resolving the final symlink can alter
        # runtime identity.
        return str(candidate.absolute())
    located = shutil.which(value, path=path_value)
    if located is None:
        raise FileNotFoundError(value)
    return str(Path(located).absolute())


def validate_argv(argv: Sequence[str]) -> tuple[str, ...]:
    if len(argv) > MAX_ARGV_ITEMS:
        raise ValueError("runtime.validation.too_many_arguments")
    values = tuple(str(item) for item in argv)
    if any("\x00" in item for item in values):
        raise ValueError("runtime.validation.invalid_argument")
    if sum(len(item.encode("utf-8")) for item in values) > MAX_ARGUMENT_BYTES:
        raise ValueError("runtime.validation.arguments_too_large")
    return values


def bounded_timeout(value: float) -> float:
    timeout = float(value)
    if not 0 < timeout <= MAX_TIMEOUT_SECONDS:
        raise ValueError("runtime.validation.invalid_timeout")
    return timeout


def is_safe_environment_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)) and not bool(
        _SENSITIVE_ENVIRONMENT_NAME.search(name)
    )


def minimal_environment(environment_names: Sequence[str] = ()) -> dict[str, str]:
    requested = tuple(dict.fromkeys((*_BASE_ENVIRONMENT_NAMES, *environment_names)))
    unsafe = [name for name in requested if not is_safe_environment_name(name)]
    if unsafe:
        raise ValueError("runtime.validation.unsafe_environment_name")
    return {name: os.environ[name] for name in requested if name in os.environ}


def sanitize_value(value: Any, *, key: str | None = None) -> Any:
    if key and _SENSITIVE_ENVIRONMENT_NAME.search(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): sanitize_value(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [sanitize_value(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return f"[bytes:{len(value)}]"
    if isinstance(value, str):
        if len(value) > MAX_SANITIZED_STRING_LENGTH:
            return value[:MAX_SANITIZED_STRING_LENGTH] + "...[truncated]"
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:MAX_SANITIZED_STRING_LENGTH]


def _reader_thread(stream: Any, capture: _BoundedCapture, name: str) -> threading.Thread:
    def read_stream() -> None:
        if stream is None:
            return
        try:
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                capture.append(chunk)
        finally:
            stream.close()

    thread = threading.Thread(target=read_stream, name=name, daemon=True)
    thread.start()
    return thread


def _terminate_process(process: subprocess.Popen[bytes], timeout: float) -> int:
    exit_code = process.poll()
    if exit_code is not None:
        return exit_code
    process.terminate()
    try:
        return process.wait(timeout=max(0.1, timeout))
    except subprocess.TimeoutExpired:
        process.kill()
        return process.wait(timeout=max(0.1, timeout))
