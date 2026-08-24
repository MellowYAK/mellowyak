from __future__ import annotations

from pathlib import Path
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
    relative_markers,
    safe_metadata_command,
    stable_metadata,
)


class NodeRuntimeAdapter(BaseRuntimeAdapter):
    name = "node"
    version = "1"
    runtime_type = "NODE"
    capabilities = (*BaseRuntimeAdapter.capabilities, "runtime.capability.node_metadata")

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        root = project.expanduser().resolve()
        manifest_candidates = (
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
        )
        markers = relative_markers(root, manifest_candidates)
        if not markers:
            return ()
        package = read_json_object(root / "package.json")
        scripts = package.get("scripts", {})
        script_names = stable_metadata(scripts.keys()) if isinstance(scripts, dict) else ()
        package_manager_name, package_manager_executable = _package_manager(root)
        node_executable = executable_on_path("node")
        version = self._version(root, node_executable)
        frameworks = _test_frameworks(package, script_names)
        limitations: list[str] = ["runtime.limitations.package_scripts_require_approval"]
        if node_executable is None:
            limitations.append("runtime.limitations.node_executable_unavailable")
        if package_manager_executable is None:
            limitations.append("runtime.limitations.package_manager_unavailable")
        metadata: dict[str, Any] = {
            "manifest_hashes": manifest_hashes(root, manifest_candidates),
            "package_manager": package_manager_name,
            "package_manager_executable": package_manager_executable,
            "scripts": script_names,
            "test_frameworks": frameworks,
            "recommended_executable": package_manager_executable or node_executable,
        }
        return (
            RuntimeDetection(
                runtime_type=self.runtime_type,
                adapter_name=self.name,
                adapter_version=self.version,
                confidence=(
                    DetectionConfidence.HIGH
                    if "package.json" in markers
                    else DetectionConfidence.MEDIUM
                ),
                markers=markers,
                executable=node_executable,
                version=version,
                reasons=("runtime.detection.node_markers",),
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
        return first_line((result[1] or result[2]) if result else "")


def _package_manager(root: Path) -> tuple[str | None, str | None]:
    if (root / "pnpm-lock.yaml").is_file():
        return "PNPM", executable_on_path("pnpm")
    if (root / "yarn.lock").is_file():
        return "YARN", executable_on_path("yarn")
    if (root / "package-lock.json").is_file() or (root / "package.json").is_file():
        return "NPM", executable_on_path("npm")
    return None, None


def _test_frameworks(package: dict[str, Any], script_names: tuple[str, ...]) -> tuple[str, ...]:
    detected: list[str] = []
    dependency_names: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        values = package.get(key, {})
        if isinstance(values, dict):
            dependency_names.update(str(item) for item in values)
    if "vitest" in dependency_names:
        detected.append("VITEST")
    if "jest" in dependency_names:
        detected.append("JEST")
    if "@playwright/test" in dependency_names or "playwright" in dependency_names:
        detected.append("PLAYWRIGHT")
    if "test" in script_names and not detected:
        detected.append("PACKAGE_SCRIPT")
    return stable_metadata(detected)
