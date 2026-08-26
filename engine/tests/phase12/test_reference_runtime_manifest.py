from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from mellowyak_engine.runtime_adapters.manifest import RuntimeManifestAdapter


def _generator_module():
    path = Path(__file__).resolve().parents[3] / "scripts" / "create_phase12m_reference_project.py"
    spec = importlib.util.spec_from_file_location("phase12_reference_generator", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rideflow_reference_declares_four_safe_runtime_profiles(tmp_path: Path) -> None:
    module = _generator_module()
    root = tmp_path / "rideflow"
    result = module.create(root, 38173, 38174)
    detections = RuntimeManifestAdapter().detect(root)
    assert result["runtime_profile_count"] == 4
    assert [item.metadata["profile"]["display_name"] for item in detections] == [
        "RideFlow Web frontend",
        "RideFlow Python API",
        "RideFlow deterministic tests",
        "RideFlow ride status CLI",
    ]
    assert {item.runtime_type for item in detections} == {"NODE", "PYTHON"}
    assert all(item.metadata["profile"]["network_policy"] == "LOOPBACK_ONLY" for item in detections)
    assert json.loads((root / ".mellowyak-reference-project.json").read_text())["synthetic"]


def test_runtime_manifest_rejects_secrets_shells_and_escaping_cwd(tmp_path: Path) -> None:
    adapter = RuntimeManifestAdapter()
    unsafe = [
        {
            "schema": "mellowyak.runtime-manifest.v1",
            "api_token": "canary",
            "profiles": [],
        },
        {
            "schema": "mellowyak.runtime-manifest.v1",
            "profiles": [
                {
                    "display_name": "Unsafe shell",
                    "runtime_type": "GENERIC_PROCESS",
                    "executable": "sh",
                    "argv": ["-c", "echo unsafe"],
                    "relative_working_directory": ".",
                }
            ],
        },
        {
            "schema": "mellowyak.runtime-manifest.v1",
            "profiles": [
                {
                    "display_name": "Escaping cwd",
                    "runtime_type": "PYTHON",
                    "executable": "python3",
                    "argv": ["-V"],
                    "relative_working_directory": "..",
                }
            ],
        },
    ]
    for payload in unsafe:
        (tmp_path / "mellowyak.runtime.json").write_text(json.dumps(payload), encoding="utf-8")
        assert adapter.detect(tmp_path) == ()
