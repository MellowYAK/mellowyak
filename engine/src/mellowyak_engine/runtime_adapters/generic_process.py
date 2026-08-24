from __future__ import annotations

from mellowyak_engine.runtime_adapters.base import BaseRuntimeAdapter, RuntimeProfileSpec


class GenericProcessRuntimeAdapter(BaseRuntimeAdapter):
    """Runs one explicitly approved executable and argv; it never auto-detects."""

    name = "generic-process"
    version = "1"
    runtime_type = "GENERIC_PROCESS"
    capabilities = (*BaseRuntimeAdapter.capabilities, "runtime.capability.generic_process")

    def fingerprint(self, profile: RuntimeProfileSpec) -> str:
        # The base fingerprint includes the exact executable and argv but no environment values.
        return super().fingerprint(profile)
