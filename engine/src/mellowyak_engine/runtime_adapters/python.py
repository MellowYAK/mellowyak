from __future__ import annotations

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
    relative_markers,
    safe_metadata_command,
    stable_metadata,
)


class PythonRuntimeAdapter(BaseRuntimeAdapter):
    name = "python"
    version = "1"
    runtime_type = "PYTHON"
    capabilities = (*BaseRuntimeAdapter.capabilities, "runtime.capability.python_metadata")

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        root = project.expanduser().resolve()
        manifests = _python_manifests(root)
        markers = relative_markers(
            root,
            (
                *manifests,
                "Pipfile",
                "poetry.lock",
                "uv.lock",
                "pytest.ini",
                "tox.ini",
                "setup.py",
                "setup.cfg",
                "manage.py",
                "app.py",
                "main.py",
            ),
        )
        virtual_environment = _virtual_environment_interpreter(root)
        if virtual_environment:
            markers = (*markers, virtual_environment.relative_to(root).as_posix())
        markers = tuple(dict.fromkeys(markers))
        if not markers:
            return ()
        executable = (
            str(virtual_environment)
            if virtual_environment
            else executable_on_path("python3", "python")
        )
        if executable is None and Path(sys.executable).is_file():
            executable = str(Path(sys.executable).resolve())
        version = self._version(root, executable)
        test_frameworks = _test_frameworks(root)
        entry_points = _entry_points(root)
        limitations: list[str] = []
        if executable is None:
            limitations.append("runtime.limitations.python_executable_unavailable")
        if not test_frameworks:
            limitations.append("runtime.limitations.test_runner_not_detected")
        metadata: dict[str, Any] = {
            "environment_kind": "PROJECT_VENV" if virtual_environment else "SYSTEM",
            "manifest_hashes": manifest_hashes(root, manifests),
            "test_frameworks": test_frameworks,
            "entry_points": entry_points,
            "recommended_executable": executable,
        }
        return (
            RuntimeDetection(
                runtime_type=self.runtime_type,
                adapter_name=self.name,
                adapter_version=self.version,
                confidence=(
                    DetectionConfidence.HIGH
                    if manifests or virtual_environment
                    else DetectionConfidence.MEDIUM
                ),
                markers=markers,
                executable=executable,
                version=version,
                reasons=("runtime.detection.python_markers",),
                limitations=tuple(limitations),
                metadata=metadata,
            ),
        )

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


def _python_manifests(root: Path) -> tuple[str, ...]:
    fixed_candidates = (
        "pyproject.toml",
        "Pipfile",
        "Pipfile.lock",
        "poetry.lock",
        "uv.lock",
        "setup.py",
        "setup.cfg",
    )
    candidates = [candidate for candidate in fixed_candidates if (root / candidate).is_file()]
    candidates.extend(
        path.relative_to(root).as_posix()
        for path in sorted(root.glob("requirements*.txt"))[:128]
        if path.is_file()
    )
    return tuple(dict.fromkeys(candidates))


def _virtual_environment_interpreter(root: Path) -> Path | None:
    for directory in (".venv", "venv", "env"):
        for relative in (("bin", "python"), ("Scripts", "python.exe")):
            candidate = (root / directory).joinpath(*relative)
            if candidate.is_file():
                # Keep the project-local venv identity even when its interpreter is a symlink.
                return candidate.absolute()
    return None


def _test_frameworks(root: Path) -> tuple[str, ...]:
    detected: list[str] = []
    if any((root / item).exists() for item in ("pytest.ini", "conftest.py")):
        detected.append("PYTEST")
    pyproject = root / "pyproject.toml"
    if pyproject.is_file() and pyproject.stat().st_size <= MAX_METADATA_FILE_BYTES:
        try:
            payload = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            payload = {}
        tool = payload.get("tool", {}) if isinstance(payload, dict) else {}
        if isinstance(tool, dict) and "pytest" in tool:
            detected.append("PYTEST")
    return stable_metadata(detected)


def _entry_points(root: Path) -> tuple[str, ...]:
    candidates = ("main.py", "app.py", "manage.py", "src/main.py")
    return stable_metadata(candidate for candidate in candidates if (root / candidate).is_file())
