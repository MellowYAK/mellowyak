from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from mellowyak_engine.runtime_adapters.base import (
    BaseRuntimeAdapter,
    DetectionConfidence,
    RuntimeDetection,
)

MANIFEST_NAME = "mellowyak.runtime.json"
MANIFEST_SCHEMA = "mellowyak.runtime-manifest.v1"
MAX_MANIFEST_BYTES = 256 * 1024
_SAFE_RUNTIME_TYPES = frozenset({"NODE", "PYTHON", "GENERIC_PROCESS"})
_SAFE_MODES = frozenset({"MANAGED", "EXTERNAL", "MANUAL"})
_SECRET_KEY = re.compile(
    r"token|secret|password|passwd|cookie|authorization|credential|api[_-]?key", re.I
)
_SHELLS = frozenset({"bash", "cmd", "cmd.exe", "dash", "fish", "powershell", "pwsh", "sh", "zsh"})


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _SECRET_KEY.search(str(key)) or _contains_secret_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_secret_key(item) for item in value)
    return False


class RuntimeManifestAdapter(BaseRuntimeAdapter):
    """Detect explicitly declared, argv-only profiles without executing the manifest."""

    name = "mellowyak_runtime_manifest"
    version = "1"
    runtime_type = "GENERIC_PROCESS"

    def detect(self, project: Path) -> tuple[RuntimeDetection, ...]:
        root = project.expanduser().resolve()
        path = root / MANIFEST_NAME
        if not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
            return ()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return ()
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != MANIFEST_SCHEMA
            or _contains_secret_key(payload)
        ):
            return ()
        profiles = payload.get("profiles")
        if not isinstance(profiles, list) or not 1 <= len(profiles) <= 16:
            return ()
        manifest_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        detections: list[RuntimeDetection] = []
        for raw in profiles:
            profile = self._profile(root, raw, manifest_digest)
            if profile is not None:
                detections.append(profile)
        return tuple(detections)

    def _profile(self, root: Path, raw: Any, manifest_digest: str) -> RuntimeDetection | None:
        if not isinstance(raw, dict) or _contains_secret_key(raw):
            return None
        name = str(raw.get("display_name", "")).strip()[:240]
        runtime_type = str(raw.get("runtime_type", "")).strip().upper()
        mode = str(raw.get("execution_mode", "MANAGED")).strip().upper()
        executable_name = str(raw.get("executable", "")).strip()
        argv = raw.get("argv", [])
        cwd = str(raw.get("relative_working_directory", ".")).strip() or "."
        ports = raw.get("expected_ports", [])
        health = raw.get("health_definition", {})
        tests = raw.get("test_definitions", [])
        if (
            not name
            or runtime_type not in _SAFE_RUNTIME_TYPES
            or mode not in _SAFE_MODES
            or not executable_name
            or Path(executable_name).name.casefold() in _SHELLS
            or not isinstance(argv, list)
            or any(not isinstance(item, str) or "\x00" in item for item in argv)
            or not isinstance(ports, list)
            or any(
                isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535
                for port in ports
            )
            or not isinstance(health, dict)
            or not isinstance(tests, list)
        ):
            return None
        try:
            working = (root / cwd).resolve(strict=True)
            working.relative_to(root)
        except (OSError, ValueError):
            return None
        if not working.is_dir():
            return None
        executable = shutil.which(executable_name)
        limitations = [] if executable else ["runtime.limitations.executable_unavailable"]
        profile = {
            "display_name": name,
            "runtime_type": runtime_type,
            "execution_mode": mode,
            "executable_reference": executable or executable_name,
            "argv": argv[:128],
            "relative_working_directory": cwd,
            "expected_ports": ports[:20],
            "health_definition": health,
            "test_definitions": tests[:50],
            "environment_schema": [],
            "network_policy": "LOOPBACK_ONLY",
            "dependency_fingerprint": manifest_digest,
            "limitations": limitations,
        }
        return RuntimeDetection(
            runtime_type=runtime_type,
            adapter_name=self.name,
            adapter_version=self.version,
            confidence=DetectionConfidence.HIGH,
            markers=(MANIFEST_NAME,),
            executable=executable,
            version=None,
            reasons=("runtime.detection.approved_manifest",),
            limitations=tuple(limitations),
            metadata={"profile": profile, "manifest_digest": manifest_digest},
        )
