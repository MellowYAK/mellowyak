from __future__ import annotations

import os
import sys
import tomllib
from pathlib import Path
from typing import Any

from mellowyak_engine.runtime_adapters.base import (
    BaseRuntimeAdapter,
    DetectionConfidence,
    RuntimeDetection,
    RuntimeProfileSpec,
)
from mellowyak_engine.runtime_adapters.helpers import (
    MAX_METADATA_FILE_BYTES,
    executable_on_path,
    first_line,
    manifest_hashes,
    safe_metadata_command,
    stable_metadata,
)
from mellowyak_engine.scanning.policy import DEFAULT_EXCLUDED_DIRS

MAX_PYTHON_PACKAGE_ROOTS = 64


class PythonRuntimeAdapter(BaseRuntimeAdapter):
    name = "python"
    version = "2"
    runtime_type = "PYTHON"
    capabilities = (*BaseRuntimeAdapter.capabilities, "runtime.capability.python_metadata")

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        root = project.expanduser().resolve()
        package_roots = _discover_python_roots(root)
        if not package_roots:
            return ()
        virtual_environment = _virtual_environment_interpreter(root)
        executable = (
            str(virtual_environment)
            if virtual_environment
            else executable_on_path("python3", "python")
        )
        if executable is None and Path(sys.executable).is_file():
            executable = str(Path(sys.executable).resolve())
        version = self._version(root, executable)
        detections: list[RuntimeDetection] = []
        for package_root in package_roots:
            relative_root = package_root.relative_to(root).as_posix() or "."
            manifests = _python_manifests(package_root)
            payload = _pyproject(package_root)
            dependencies = _dependencies(payload)
            test_frameworks = _test_frameworks(package_root, payload, dependencies)
            entry_points = _entry_points(package_root, payload)
            frameworks = _frameworks(dependencies, entry_points)
            package_manager = _package_manager(package_root, root)
            expected_ports = _expected_ports(frameworks)
            health = (
                {"kind": "HTTP", "url": f"http://127.0.0.1:{expected_ports[0]}/"}
                if expected_ports
                else {}
            )
            limitations: list[str] = ["runtime.limitations.commands_require_approval"]
            if executable is None:
                limitations.append("runtime.limitations.python_executable_unavailable")
            if not test_frameworks:
                limitations.append("runtime.limitations.test_runner_not_detected")
            if len(package_roots) >= MAX_PYTHON_PACKAGE_ROOTS:
                limitations.append("runtime.limitations.package_root_limit_reached")
            test_commands = _test_commands(executable, relative_root, test_frameworks)
            development_commands = _development_commands(
                executable, relative_root, frameworks, entry_points
            )
            markers = tuple(
                dict.fromkeys(
                    path.relative_to(root).as_posix()
                    for name in (
                        *manifests,
                        "pytest.ini",
                        "tox.ini",
                        "manage.py",
                        "app.py",
                        "main.py",
                    )
                    if (path := package_root / name).is_file()
                )
            )
            if virtual_environment:
                markers = (*markers, virtual_environment.relative_to(root).as_posix())
            profile = {
                "display_name": _project_name(payload) or package_root.name or "Python",
                "runtime_type": self.runtime_type,
                "execution_mode": "MANAGED",
                "executable_reference": executable,
                "argv": [],
                "relative_working_directory": relative_root,
                "expected_ports": list(expected_ports),
                "health_definition": health,
                "test_definitions": list(test_commands),
                "environment_schema": [],
                "network_policy": "LOOPBACK_ONLY",
                "limitations": limitations,
            }
            metadata: dict[str, Any] = {
                "environment_kind": "PROJECT_VENV" if virtual_environment else "SYSTEM",
                "manifest_hashes": manifest_hashes(package_root, manifests),
                "package_manager": package_manager,
                "runtime_owner": "PROJECT_ROOT" if relative_root == "." else "PACKAGE",
                "workspace_root": ".",
                "package_root": relative_root,
                "package_roots": tuple(
                    item.relative_to(root).as_posix() or "." for item in package_roots
                ),
                "test_frameworks": test_frameworks,
                "entry_points": entry_points,
                "frameworks": frameworks,
                "test_commands": test_commands,
                "development_commands": development_commands,
                "expected_ports": expected_ports,
                "health_checks": (health,) if health else (),
                "recommended_executable": executable,
                "profile": profile,
            }
            detections.append(
                RuntimeDetection(
                    runtime_type=self.runtime_type,
                    adapter_name=self.name,
                    adapter_version=self.version,
                    confidence=DetectionConfidence.HIGH,
                    markers=markers,
                    executable=executable,
                    version=version,
                    reasons=("runtime.detection.python_project_markers",),
                    limitations=tuple(dict.fromkeys(limitations)),
                    metadata=metadata,
                )
            )
        return tuple(detections)

    def executable_version(self, profile: RuntimeProfileSpec) -> str | None:
        return self._version(profile.project_root.expanduser().resolve(), profile.executable)

    def _version(self, root: Path, executable: str | None) -> str | None:
        result = safe_metadata_command(
            runner=self.runner,
            project=root,
            executable=executable,
            argv=("--version",),
        )
        if result is None:
            return None
        _, stdout, stderr = result
        return first_line(stdout or stderr)


def _discover_python_roots(root: Path) -> tuple[Path, ...]:
    result: list[Path] = []
    markers = {"pyproject.toml", "setup.py", "setup.cfg"}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories[:] = sorted(
            item
            for item in directories
            if item not in DEFAULT_EXCLUDED_DIRS and not (Path(current) / item).is_symlink()
        )
        current_path = Path(current)
        if markers.intersection(files) or any(
            name.startswith("requirements") and name.endswith(".txt") for name in files
        ):
            result.append(current_path)
            if len(result) >= MAX_PYTHON_PACKAGE_ROOTS:
                break
    return tuple(result)


def _python_manifests(root: Path) -> tuple[str, ...]:
    fixed = (
        "pyproject.toml",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "uv.lock",
        "setup.py",
        "setup.cfg",
    )
    candidates = [name for name in fixed if (root / name).is_file()]
    candidates.extend(
        path.name for path in sorted(root.glob("requirements*.txt"))[:128] if path.is_file()
    )
    return tuple(dict.fromkeys(candidates))


def _virtual_environment_interpreter(root: Path) -> Path | None:
    for directory in (".venv", "venv", "env"):
        for relative in (("bin", "python"), ("Scripts", "python.exe")):
            candidate = (root / directory).joinpath(*relative)
            if candidate.is_file():
                return candidate.absolute()
    return None


def _pyproject(root: Path) -> dict[str, Any]:
    path = root / "pyproject.toml"
    if not path.is_file() or path.stat().st_size > MAX_METADATA_FILE_BYTES:
        return {}
    try:
        result = tomllib.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result, dict) else {}
    except (OSError, UnicodeError, tomllib.TOMLDecodeError):
        return {}


def _project_name(payload: dict[str, Any]) -> str:
    project = payload.get("project", {})
    return str(project.get("name", ""))[:240] if isinstance(project, dict) else ""


def _dependencies(payload: dict[str, Any]) -> tuple[str, ...]:
    result: list[str] = []
    project = payload.get("project", {})
    if isinstance(project, dict):
        raw = project.get("dependencies", ())
        if isinstance(raw, list):
            result.extend(
                str(item).split("[")[0].split("=")[0].split(">")[0].strip().casefold()
                for item in raw
            )
    poetry = payload.get("tool", {})
    poetry = poetry.get("poetry", {}) if isinstance(poetry, dict) else {}
    raw_poetry = poetry.get("dependencies", {}) if isinstance(poetry, dict) else {}
    if isinstance(raw_poetry, dict):
        result.extend(str(item).casefold() for item in raw_poetry)
    return stable_metadata(result)


def _test_frameworks(
    root: Path, payload: dict[str, Any], dependencies: tuple[str, ...]
) -> tuple[str, ...]:
    detected: list[str] = []
    tool = payload.get("tool", {})
    if (
        any((root / item).exists() for item in ("pytest.ini", "conftest.py"))
        or "pytest" in dependencies
        or isinstance(tool, dict)
        and "pytest" in tool
    ):
        detected.append("PYTEST")
    if any(path.name.startswith("test") for path in root.glob("test*.py")) and not detected:
        detected.append("UNITTEST")
    return stable_metadata(detected)


def _entry_points(root: Path, payload: dict[str, Any]) -> tuple[str, ...]:
    result = [
        name
        for name in ("main.py", "app.py", "manage.py", "src/main.py")
        if (root / name).is_file()
    ]
    project = payload.get("project", {})
    scripts = project.get("scripts", {}) if isinstance(project, dict) else {}
    if isinstance(scripts, dict):
        result.extend(f"console:{name}" for name in scripts)
    return stable_metadata(result)


def _frameworks(dependencies: tuple[str, ...], entry_points: tuple[str, ...]) -> tuple[str, ...]:
    result = [
        label
        for dependency, label in (
            ("flask", "FLASK"),
            ("fastapi", "FASTAPI"),
            ("django", "DJANGO"),
            ("datasette", "DATASETTE"),
        )
        if dependency in dependencies
    ]
    if any(item == "console:datasette" for item in entry_points):
        result.append("DATASETTE")
    return stable_metadata(result)


def _package_manager(package_root: Path, root: Path) -> str:
    for directory in (package_root, root):
        if (directory / "uv.lock").is_file():
            return "UV"
        if (directory / "poetry.lock").is_file():
            return "POETRY"
        if (directory / "Pipfile.lock").is_file():
            return "PIPENV"
    return "PIP"


def _expected_ports(frameworks: tuple[str, ...]) -> tuple[int, ...]:
    if "FLASK" in frameworks:
        return (5000,)
    if "DATASETTE" in frameworks:
        return (8001,)
    if "FASTAPI" in frameworks or "DJANGO" in frameworks:
        return (8000,)
    return ()


def _test_commands(
    executable: str | None, cwd: str, frameworks: tuple[str, ...]
) -> tuple[dict[str, Any], ...]:
    if executable is None:
        return ()
    module = "pytest" if "PYTEST" in frameworks else "unittest"
    return (
        {
            "probe_type": "TEST",
            "executable": executable,
            "argv": ["-m", module] + ([] if module == "pytest" else ["discover"]),
            "relative_working_directory": cwd,
            "requires_approval": True,
        },
    )


def _development_commands(
    executable: str | None,
    cwd: str,
    frameworks: tuple[str, ...],
    entry_points: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    if executable is None:
        return ()
    commands: list[dict[str, Any]] = []
    if "FLASK" in frameworks:
        commands.append(
            {
                "executable": executable,
                "argv": ["-m", "flask", "run"],
                "relative_working_directory": cwd,
                "requires_approval": True,
            }
        )
    if "DJANGO" in frameworks and "manage.py" in entry_points:
        commands.append(
            {
                "executable": executable,
                "argv": ["manage.py", "runserver", "127.0.0.1:8000"],
                "relative_working_directory": cwd,
                "requires_approval": True,
            }
        )
    if "DATASETTE" in frameworks:
        commands.append(
            {
                "executable": executable,
                "argv": ["-m", "datasette", "--help"],
                "relative_working_directory": cwd,
                "requires_approval": True,
            }
        )
    return tuple(commands[:8])
