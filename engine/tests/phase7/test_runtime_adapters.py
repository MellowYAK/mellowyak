from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from mellowyak_engine.runtime_adapters import (
    GenericProcessRuntimeAdapter,
    JavaMetadataRuntimeAdapter,
    NodeRuntimeAdapter,
    OperationStatus,
    PhpRuntimeAdapter,
    PythonRuntimeAdapter,
    RubyMetadataRuntimeAdapter,
    RuntimeProbeSpec,
    RuntimeProfileSpec,
    RuntimeState,
)
from mellowyak_engine.runtime_adapters.base import ProcessExecution, minimal_environment
from mellowyak_engine.runtime_profiles.detection import RuntimeDetectionService
from mellowyak_engine.runtime_profiles.validation import validate_runtime_profile


def _profile(root: Path, **overrides: object) -> RuntimeProfileSpec:
    values: dict[str, object] = {
        "profile_id": "profile-1",
        "project_root": root,
        "runtime_type": "GENERIC_PROCESS",
        "executable": sys.executable,
        "approved": True,
        "output_limit_bytes": 1024,
    }
    values.update(overrides)
    return RuntimeProfileSpec(**values)  # type: ignore[arg-type]


def test_detects_python_project_and_prefers_project_virtual_environment(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'fixture'\n[tool.pytest.ini_options]\naddopts = '-q'\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('fixture')\n", encoding="utf-8")
    interpreter = tmp_path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    interpreter.mkdir(parents=True)
    executable = interpreter / ("python.exe" if os.name == "nt" else "python")
    if os.name == "nt":
        executable.write_bytes(Path(sys.executable).read_bytes())
    else:
        executable.symlink_to(Path(sys.executable).resolve())

    detection = PythonRuntimeAdapter().detect(tmp_path)[0]

    assert detection.runtime_type == "PYTHON"
    assert detection.executable == str(executable.absolute())
    assert detection.metadata["environment_kind"] == "PROJECT_VENV"
    assert detection.metadata["test_frameworks"] == ("PYTEST",)
    assert detection.metadata["entry_points"] == ("main.py",)
    assert set(detection.metadata["manifest_hashes"]) == {
        "pyproject.toml",
        "requirements-dev.txt",
    }
    assert all(len(value) == 64 for value in detection.metadata["manifest_hashes"].values())


def test_node_detection_reads_safe_metadata_without_running_package_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = {
        "scripts": {"dev": "touch should-never-exist", "test": "vitest run"},
        "devDependencies": {"vitest": "1.0.0", "@playwright/test": "1.0.0"},
    }
    (tmp_path / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    invoked: list[tuple[str, ...]] = []

    class RecordingRunner:
        def run(self, **kwargs: object) -> object:
            invoked.append(tuple(kwargs["argv"]))  # type: ignore[arg-type]
            raise FileNotFoundError

    adapter = NodeRuntimeAdapter(runner=RecordingRunner())  # type: ignore[arg-type]
    monkeypatch.setattr(
        "mellowyak_engine.runtime_adapters.node.executable_on_path",
        lambda *names: f"/runtime/{names[0]}",
    )

    detection = adapter.detect(tmp_path)[0]

    assert detection.metadata["scripts"] == ("dev", "test")
    assert detection.metadata["test_frameworks"] == ("PLAYWRIGHT", "VITEST")
    assert "touch should-never-exist" not in repr(detection.metadata)
    assert invoked == [("--version",)]
    assert not (tmp_path / "should-never-exist").exists()


def test_php_detection_is_available_without_php_and_never_persists_phpinfo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "composer.json").write_text("{}", encoding="utf-8")
    (tmp_path / "composer.lock").write_text("{}", encoding="utf-8")
    (tmp_path / "phpunit.xml").write_text("<phpunit/>", encoding="utf-8")
    monkeypatch.setattr(
        "mellowyak_engine.runtime_adapters.php.executable_on_path", lambda *names: None
    )

    detection = PhpRuntimeAdapter().detect(tmp_path)[0]

    assert detection.runtime_type == "PHP"
    assert detection.executable is None
    assert detection.metadata["sapi"] is None
    assert detection.metadata["extensions"] == ()
    assert detection.metadata["test_frameworks"] == ("PHPUNIT",)
    assert "phpinfo" not in repr(detection.metadata).lower()
    assert "runtime.limitations.implemented_not_runtime_verified" in detection.limitations


def test_php_metadata_uses_only_fixed_bounded_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "composer.json").write_text("{}", encoding="utf-8")
    invoked: list[tuple[str, ...]] = []

    class PhpMetadataRunner:
        def run(self, **kwargs: object) -> ProcessExecution:
            argv = tuple(kwargs["argv"])  # type: ignore[arg-type]
            invoked.append(argv)
            stdout = {
                ("--version",): "PHP 8.3.0 (cli)",
                ("-r", "echo PHP_SAPI;"): "cli",
                (
                    "-r",
                    "echo json_encode(get_loaded_extensions());",
                ): '["json","PDO"]',
            }[argv]
            return ProcessExecution(
                executable="/runtime/php",
                argv=argv,
                working_directory=str(tmp_path),
                exit_code=0,
                duration_seconds=0.01,
                stdout=stdout,
                stderr="",
                stdout_truncated=False,
                stderr_truncated=False,
                timed_out=False,
                cancelled=False,
            )

    monkeypatch.setattr(
        "mellowyak_engine.runtime_adapters.php.executable_on_path",
        lambda *names: "/runtime/php" if names[0] == "php" else None,
    )
    detection = PhpRuntimeAdapter(runner=PhpMetadataRunner()).detect(tmp_path)[0]  # type: ignore[arg-type]

    assert detection.version == "PHP 8.3.0 (cli)"
    assert detection.metadata["sapi"] == "cli"
    assert detection.metadata["extensions"] == ("PDO", "json")
    assert invoked == [
        ("--version",),
        ("-r", "echo PHP_SAPI;"),
        ("-r", "echo json_encode(get_loaded_extensions());"),
    ]
    assert all("phpinfo" not in " ".join(argv).lower() for argv in invoked)


@pytest.mark.parametrize(
    ("adapter", "marker", "runtime_type"),
    [
        (RubyMetadataRuntimeAdapter(), "Gemfile", "RUBY"),
        (JavaMetadataRuntimeAdapter(), "pom.xml", "JAVA"),
    ],
)
def test_ruby_and_java_are_detected_as_metadata_only(
    tmp_path: Path, adapter: object, marker: str, runtime_type: str
) -> None:
    (tmp_path / marker).write_text("fixture", encoding="utf-8")

    detection = adapter.detect(tmp_path)[0]  # type: ignore[attr-defined]
    description = adapter.describe(tmp_path)  # type: ignore[attr-defined]

    assert detection.runtime_type == runtime_type
    assert "runtime.limitations.metadata_only_adapter" in detection.limitations
    assert description.execution_supported is False
    start_result = adapter.start(_profile(tmp_path))  # type: ignore[attr-defined]
    assert start_result.status == OperationStatus.UNSUPPORTED


def test_generic_probe_uses_argv_without_shell_and_bounds_output(tmp_path: Path) -> None:
    adapter = GenericProcessRuntimeAdapter()
    injected_path = tmp_path / "must-not-exist"
    literal_argument = f"hello; touch {injected_path}"
    probe = RuntimeProbeSpec(
        probe_id="probe-1",
        executable=sys.executable,
        argv=(
            "-c",
            "import sys; print(sys.argv[1]); print('x' * 200000)",
            literal_argument,
        ),
        approved=True,
        timeout_seconds=5,
        output_limit_bytes=1024,
        stdout_contains=literal_argument,
    )

    result = adapter.run_probe(_profile(tmp_path), probe)

    assert result.status == OperationStatus.SUCCEEDED
    assert result.exit_code == 0
    assert result.stdout_truncated is True
    assert len(result.stdout.encode("utf-8")) <= 1024
    assert result.assertions == {"exit_code": True, "stdout_contains": True}
    assert not injected_path.exists()


def test_very_small_output_limit_remains_physically_bounded(tmp_path: Path) -> None:
    result = GenericProcessRuntimeAdapter().run_probe(
        _profile(tmp_path),
        RuntimeProbeSpec(
            probe_id="small-output",
            executable=sys.executable,
            argv=("-c", "print('x' * 1000)"),
            approved=True,
            output_limit_bytes=8,
        ),
    )

    assert result.status == OperationStatus.SUCCEEDED
    assert result.stdout_truncated is True
    assert len(result.stdout.encode("utf-8")) <= 8


def test_execution_requires_approval_and_working_directory_is_scoped(tmp_path: Path) -> None:
    adapter = GenericProcessRuntimeAdapter()
    unapproved = _profile(
        tmp_path,
        approved=False,
        argv=("-c", "print('not started')"),
    )

    assert adapter.start(unapproved).status == OperationStatus.UNAPPROVED

    escaped = _profile(tmp_path, relative_working_directory="..")
    validation = adapter.validate(escaped)
    assert validation.valid is False
    assert "runtime.validation.invalid_working_directory" in validation.errors

    unsupported_probe = adapter.run_probe(
        _profile(tmp_path), RuntimeProbeSpec(probe_id="browser", kind="BROWSER", approved=True)
    )
    assert unsupported_probe.status == OperationStatus.UNSUPPORTED

    shell_profile = _profile(tmp_path, executable="sh")
    assert "runtime.validation.shell_executable_denied" in adapter.validate(shell_profile).errors


def test_managed_process_can_be_observed_and_stopped(tmp_path: Path) -> None:
    adapter = GenericProcessRuntimeAdapter()
    profile = _profile(tmp_path, argv=("-c", "import time; print('ready'); time.sleep(10)"))

    started = adapter.start(profile, correlation_id="correlation-1")

    assert started.status == OperationStatus.SUCCEEDED
    assert started.instance is not None
    observed = adapter.observe(profile, "correlation-1")
    assert observed.status == OperationStatus.SUCCEEDED
    assert observed.state == RuntimeState.RUNNING
    assert observed.running is True
    stopped = adapter.stop(started.instance)
    assert stopped.status == OperationStatus.SUCCEEDED
    assert (
        adapter.observe_instance(profile, started.instance, "correlation-2").state
        == RuntimeState.EXITED
    )


def test_environment_and_events_are_redacted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = GenericProcessRuntimeAdapter()
    monkeypatch.setenv("MELLOWYAK_SAFE_FLAG", "safe")
    monkeypatch.setenv("MELLOWYAK_API_TOKEN", "private")

    environment = minimal_environment(("MELLOWYAK_SAFE_FLAG",))
    assert environment["MELLOWYAK_SAFE_FLAG"] == "safe"
    with pytest.raises(ValueError, match="unsafe_environment_name"):
        minimal_environment(("MELLOWYAK_API_TOKEN",))

    sanitized = adapter.sanitize(
        {
            "event": "runtime",
            "api_token": "private",
            "nested": {"password": "private", "status": "ok"},
        }
    )
    assert sanitized == {
        "event": "runtime",
        "api_token": "[REDACTED]",
        "nested": {"password": "[REDACTED]", "status": "ok"},
    }

    first = _profile(tmp_path, metadata={"api_token": "one"})
    second = _profile(tmp_path, metadata={"api_token": "two"})
    assert adapter.fingerprint(first) == adapter.fingerprint(second)


def test_detection_is_fail_open_when_one_adapter_fails(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")

    class BrokenAdapter:
        name = "broken"
        version = "1"
        runtime_type = "BROKEN"

        def detect(self, project: Path) -> tuple[()]:
            del project
            raise OSError("fixture failure")

    report = RuntimeDetectionService(
        adapters=(BrokenAdapter(), PythonRuntimeAdapter())  # type: ignore[arg-type]
    ).detect(tmp_path)

    assert [item.runtime_type for item in report.detections] == ["PYTHON"]
    assert report.failures[0].adapter_name == "broken"
    assert report.failures[0].reason == "runtime.detection.adapter_failed"


def test_profile_validation_selects_adapter_and_reports_unknown_runtime(tmp_path: Path) -> None:
    valid_report = validate_runtime_profile(
        _profile(tmp_path), adapters=(GenericProcessRuntimeAdapter(),)
    )
    unknown_report = validate_runtime_profile(
        _profile(tmp_path, runtime_type="UNKNOWN"),
        adapters=(GenericProcessRuntimeAdapter(),),
    )

    assert valid_report.adapter_name == "generic-process"
    assert valid_report.validation.valid is True
    assert valid_report.availability is not None
    assert valid_report.availability.available is True
    assert unknown_report.adapter_name is None
    assert unknown_report.validation.errors == ("runtime.validation.adapter_unavailable",)
