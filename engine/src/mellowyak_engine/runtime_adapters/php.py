from __future__ import annotations

import json
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
    relative_markers,
    safe_metadata_command,
    stable_metadata,
)


class PhpRuntimeAdapter(BaseRuntimeAdapter):
    name = "php"
    version = "1"
    runtime_type = "PHP"
    capabilities = (*BaseRuntimeAdapter.capabilities, "runtime.capability.php_metadata")

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        root = project.expanduser().resolve()
        manifest_candidates = (
            "composer.json",
            "composer.lock",
            "phpunit.xml",
            "phpunit.xml.dist",
            "artisan",
        )
        markers = relative_markers(root, manifest_candidates)
        if not markers:
            return ()
        executable = executable_on_path("php")
        version = self._version(root, executable)
        sapi, extensions = self._safe_runtime_metadata(root, executable)
        test_frameworks = stable_metadata(
            ["PHPUNIT"]
            if any(marker in markers for marker in ("phpunit.xml", "phpunit.xml.dist"))
            else []
        )
        limitations: list[str] = []
        if executable is None:
            limitations.extend(
                (
                    "runtime.limitations.php_executable_unavailable",
                    "runtime.limitations.implemented_not_runtime_verified",
                )
            )
        metadata: dict[str, Any] = {
            "manifest_hashes": manifest_hashes(root, manifest_candidates),
            "sapi": sapi,
            "extensions": extensions,
            "test_frameworks": test_frameworks,
            "composer_executable": executable_on_path("composer"),
            "recommended_executable": executable,
        }
        return (
            RuntimeDetection(
                runtime_type=self.runtime_type,
                adapter_name=self.name,
                adapter_version=self.version,
                confidence=(
                    DetectionConfidence.HIGH
                    if "composer.json" in markers
                    else DetectionConfidence.MEDIUM
                ),
                markers=markers,
                executable=executable,
                version=version,
                reasons=("runtime.detection.php_markers",),
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

    def _safe_runtime_metadata(
        self, root: Path, executable: str | None
    ) -> tuple[str | None, tuple[str, ...]]:
        sapi_result = safe_metadata_command(
            runner=self.runner,
            project=root,
            executable=executable,
            argv=("-r", "echo PHP_SAPI;"),
        )
        sapi = first_line(sapi_result[1]) if sapi_result and sapi_result[0] == 0 else None
        extensions_result = safe_metadata_command(
            runner=self.runner,
            project=root,
            executable=executable,
            argv=("-r", "echo json_encode(get_loaded_extensions());"),
        )
        extensions: tuple[str, ...] = ()
        if extensions_result and extensions_result[0] == 0:
            try:
                values = json.loads(extensions_result[1])
            except json.JSONDecodeError:
                values = []
            if isinstance(values, list):
                extensions = stable_metadata(str(item) for item in values)
        return sapi, extensions
