from __future__ import annotations

from pathlib import Path
from typing import Any

from mellowyak_engine.runtime_adapters.base import (
    BaseRuntimeAdapter,
    DetectionConfidence,
    RuntimeDetection,
)
from mellowyak_engine.runtime_adapters.helpers import (
    executable_on_path,
    first_line,
    manifest_hashes,
    relative_markers,
    safe_metadata_command,
)


class RubyMetadataRuntimeAdapter(BaseRuntimeAdapter):
    name = "ruby-metadata"
    version = "1"
    runtime_type = "RUBY"
    execution_supported = False
    capabilities = (
        "runtime.capability.detect",
        "runtime.capability.describe",
        "runtime.capability.fingerprint",
    )

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        root = project.expanduser().resolve()
        candidates = ["Gemfile", "Gemfile.lock", ".ruby-version", "Rakefile"]
        candidates.extend(
            path.relative_to(root).as_posix()
            for path in sorted(root.glob("*.gemspec"))[:128]
            if path.is_file()
        )
        markers = relative_markers(root, candidates)
        if not markers:
            return ()
        executable = executable_on_path("ruby")
        result = safe_metadata_command(
            runner=self.runner,
            project=root,
            executable=executable,
            argv=("--version",),
        )
        version = first_line((result[1] or result[2]) if result else "")
        limitations = ["runtime.limitations.metadata_only_adapter"]
        if executable is None:
            limitations.append("runtime.limitations.ruby_executable_unavailable")
        metadata: dict[str, Any] = {
            "manifest_hashes": manifest_hashes(root, candidates),
            "recommended_executable": executable,
        }
        return (
            RuntimeDetection(
                runtime_type=self.runtime_type,
                adapter_name=self.name,
                adapter_version=self.version,
                confidence=DetectionConfidence.HIGH,
                markers=markers,
                executable=executable,
                version=version,
                reasons=("runtime.detection.ruby_markers",),
                limitations=tuple(limitations),
                metadata=metadata,
            ),
        )
