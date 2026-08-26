from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

from mellowyak_engine.runtime_adapters.base import (
    BaseRuntimeAdapter,
    DetectionConfidence,
    RuntimeDetection,
    RuntimeProfileSpec,
)
from mellowyak_engine.runtime_adapters.helpers import (
    executable_on_path,
    first_line,
    manifest_hashes,
    read_json_object,
    safe_metadata_command,
    stable_metadata,
)
from mellowyak_engine.scanning.policy import DEFAULT_EXCLUDED_DIRS

MAX_NODE_PACKAGE_ROOTS = 128
_SAFE_SCRIPT_NAME = re.compile(r"^[A-Za-z0-9:_-]{1,120}$")


class NodeRuntimeAdapter(BaseRuntimeAdapter):
    name = "node"
    version = "2"
    runtime_type = "NODE"
    capabilities = (*BaseRuntimeAdapter.capabilities, "runtime.capability.node_metadata")

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        root = project.expanduser().resolve()
        package_roots = _discover_package_roots(root)
        if not package_roots and not any(
            (root / marker).is_file()
            for marker in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
        ):
            return ()
        root_package = read_json_object(root / "package.json")
        workspace_patterns = _workspace_patterns(root, root_package)
        package_manager_name, package_manager_executable = _package_manager(root, root_package)
        node_executable = executable_on_path("node")
        version = self._version(root, node_executable)
        detections: list[RuntimeDetection] = []
        for package_root in package_roots or (root,):
            package = read_json_object(package_root / "package.json")
            relative_root = package_root.relative_to(root).as_posix() or "."
            scripts = package.get("scripts", {})
            script_names = (
                stable_metadata(
                    str(name)
                    for name in scripts
                    if _SAFE_SCRIPT_NAME.fullmatch(str(name)) is not None
                )
                if isinstance(scripts, dict)
                else ()
            )
            frameworks = _frameworks(package)
            test_frameworks = _test_frameworks(package, script_names)
            owner = _runtime_owner(relative_root, workspace_patterns)
            expected_ports = _expected_ports(frameworks, script_names)
            health = (
                {"kind": "HTTP", "url": f"http://127.0.0.1:{expected_ports[0]}/"}
                if expected_ports
                else {}
            )
            limitations = ["runtime.limitations.package_scripts_require_approval"]
            if node_executable is None:
                limitations.append("runtime.limitations.node_executable_unavailable")
            if package_manager_executable is None:
                limitations.append("runtime.limitations.package_manager_unavailable")
            if len(package_roots) >= MAX_NODE_PACKAGE_ROOTS:
                limitations.append("runtime.limitations.package_root_limit_reached")
            test_definitions = _command_definitions(
                package_manager_executable,
                relative_root,
                tuple(name for name in script_names if name == "test" or name.startswith("test:")),
                "TEST",
            )
            development_definitions = _command_definitions(
                package_manager_executable,
                relative_root,
                tuple(name for name in ("dev", "start", "serve") if name in script_names),
                "PROCESS",
            )
            markers = _relative_markers(
                root,
                package_root,
                ("package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"),
            )
            profile = {
                "display_name": str(package.get("name") or package_root.name or "Node")[:240],
                "runtime_type": self.runtime_type,
                "execution_mode": "MANAGED",
                "executable_reference": package_manager_executable or node_executable,
                "argv": [],
                "relative_working_directory": relative_root,
                "expected_ports": list(expected_ports),
                "health_definition": health,
                "test_definitions": list(test_definitions),
                "environment_schema": [],
                "network_policy": "LOOPBACK_ONLY",
                "limitations": limitations,
            }
            metadata: dict[str, Any] = {
                "manifest_hashes": manifest_hashes(
                    package_root,
                    tuple(
                        marker
                        for marker in (
                            "package.json",
                            "package-lock.json",
                            "pnpm-lock.yaml",
                            "yarn.lock",
                        )
                        if (package_root / marker).is_file()
                    ),
                ),
                "package_manager": package_manager_name,
                "package_manager_executable": package_manager_executable,
                "package_name": str(package.get("name") or "")[:240],
                "runtime_owner": owner,
                "workspace_root": ".",
                "package_root": relative_root,
                "package_roots": tuple(
                    item.relative_to(root).as_posix() or "." for item in package_roots
                ),
                "workspace_patterns": workspace_patterns,
                "scripts": script_names,
                "frameworks": frameworks,
                "test_frameworks": test_frameworks,
                "test_commands": test_definitions,
                "development_commands": development_definitions,
                "expected_ports": expected_ports,
                "health_checks": (health,) if health else (),
                "recommended_executable": package_manager_executable or node_executable,
                "profile": profile,
            }
            detections.append(
                RuntimeDetection(
                    runtime_type=self.runtime_type,
                    adapter_name=self.name,
                    adapter_version=self.version,
                    confidence=DetectionConfidence.HIGH,
                    markers=markers,
                    executable=node_executable,
                    version=version,
                    reasons=("runtime.detection.node_workspace_markers",),
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
        return first_line((result[1] or result[2]) if result else "")


def _discover_package_roots(root: Path) -> tuple[Path, ...]:
    result: list[Path] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        directories[:] = sorted(
            item
            for item in directories
            if item not in DEFAULT_EXCLUDED_DIRS and not (Path(current) / item).is_symlink()
        )
        current_path = Path(current)
        try:
            current_path.resolve(strict=False).relative_to(root)
        except ValueError:
            directories[:] = []
            continue
        if "package.json" in files:
            result.append(current_path)
            if len(result) >= MAX_NODE_PACKAGE_ROOTS:
                break
    return tuple(result)


def _workspace_patterns(root: Path, package: dict[str, Any]) -> tuple[str, ...]:
    raw = package.get("workspaces", ())
    if isinstance(raw, dict):
        raw = raw.get("packages", ())
    patterns = (
        [str(item).strip().rstrip("/") for item in raw if isinstance(item, str)]
        if isinstance(raw, list)
        else []
    )
    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.is_file() and pnpm.stat().st_size <= 256_000:
        try:
            for line in pnpm.read_text(encoding="utf-8", errors="replace").splitlines():
                match = re.match(r"\s*-\s*['\"]?([^'\"#]+?)['\"]?\s*$", line)
                if match:
                    patterns.append(match.group(1).strip().rstrip("/"))
        except OSError:
            pass
    return stable_metadata(patterns)


def _runtime_owner(relative_root: str, patterns: tuple[str, ...]) -> str:
    if relative_root == ".":
        return "WORKSPACE" if patterns else "PROJECT_ROOT"
    path = PurePosixPath(relative_root)
    return "WORKSPACE_PACKAGE" if any(path.match(pattern) for pattern in patterns) else "PACKAGE"


def _relative_markers(root: Path, package_root: Path, names: tuple[str, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for name in names:
        path = package_root / name
        if path.is_file():
            result.append(path.relative_to(root).as_posix())
    for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "pnpm-workspace.yaml"):
        path = root / name
        if path.is_file():
            result.append(path.relative_to(root).as_posix())
    return tuple(dict.fromkeys(result))


def _package_manager(root: Path, package: dict[str, Any]) -> tuple[str | None, str | None]:
    declared = str(package.get("packageManager", "")).partition("@")[0].casefold()
    if (root / "pnpm-lock.yaml").is_file() or declared == "pnpm":
        return "PNPM", executable_on_path("pnpm")
    if (root / "yarn.lock").is_file() or declared == "yarn":
        return "YARN", executable_on_path("yarn")
    if (root / "package-lock.json").is_file() or (root / "package.json").is_file():
        return "NPM", executable_on_path("npm")
    return None, None


def _dependency_names(package: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        values = package.get(key, {})
        if isinstance(values, dict):
            result.update(str(item) for item in values)
    return result


def _frameworks(package: dict[str, Any]) -> tuple[str, ...]:
    names = _dependency_names(package)
    return stable_metadata(
        label
        for dependency, label in (
            ("react", "REACT"),
            ("vite", "VITE"),
            ("next", "NEXT"),
            ("express", "EXPRESS"),
            ("@tauri-apps/api", "TAURI"),
        )
        if dependency in names
    )


def _test_frameworks(package: dict[str, Any], script_names: tuple[str, ...]) -> tuple[str, ...]:
    names = _dependency_names(package)
    detected = [
        label
        for dependency, label in (
            ("vitest", "VITEST"),
            ("jest", "JEST"),
            ("@playwright/test", "PLAYWRIGHT"),
            ("playwright", "PLAYWRIGHT"),
        )
        if dependency in names
    ]
    if "test" in script_names and not detected:
        detected.append("PACKAGE_SCRIPT")
    return stable_metadata(detected)


def _expected_ports(frameworks: tuple[str, ...], scripts: tuple[str, ...]) -> tuple[int, ...]:
    if not any(item in scripts for item in ("dev", "start", "serve")):
        return ()
    if "VITE" in frameworks:
        return (5173,)
    return (3000,)


def _command_definitions(
    executable: str | None,
    cwd: str,
    scripts: tuple[str, ...],
    probe_type: str,
) -> tuple[dict[str, Any], ...]:
    if executable is None:
        return ()
    return tuple(
        {
            "probe_type": probe_type,
            "executable": executable,
            "argv": ["run", script],
            "relative_working_directory": cwd,
            "requires_approval": True,
        }
        for script in scripts[:16]
    )
