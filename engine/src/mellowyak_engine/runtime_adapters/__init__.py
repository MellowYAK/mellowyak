from mellowyak_engine.runtime_adapters.base import (
    BaseRuntimeAdapter,
    DetectionConfidence,
    OperationStatus,
    RuntimeAdapter,
    RuntimeAvailability,
    RuntimeDescription,
    RuntimeDetection,
    RuntimeInstance,
    RuntimeObservation,
    RuntimeProbeResult,
    RuntimeProbeSpec,
    RuntimeProfileSpec,
    RuntimeStartResult,
    RuntimeState,
    RuntimeStopResult,
    RuntimeValidation,
    SafeProcessRunner,
)
from mellowyak_engine.runtime_adapters.generic_process import GenericProcessRuntimeAdapter
from mellowyak_engine.runtime_adapters.java import JavaMetadataRuntimeAdapter
from mellowyak_engine.runtime_adapters.manifest import RuntimeManifestAdapter
from mellowyak_engine.runtime_adapters.node import NodeRuntimeAdapter
from mellowyak_engine.runtime_adapters.php import PhpRuntimeAdapter
from mellowyak_engine.runtime_adapters.python import PythonRuntimeAdapter
from mellowyak_engine.runtime_adapters.ruby import RubyMetadataRuntimeAdapter

DEFAULT_RUNTIME_ADAPTERS: tuple[RuntimeAdapter, ...] = (
    RuntimeManifestAdapter(),
    PythonRuntimeAdapter(),
    NodeRuntimeAdapter(),
    PhpRuntimeAdapter(),
    RubyMetadataRuntimeAdapter(),
    JavaMetadataRuntimeAdapter(),
    GenericProcessRuntimeAdapter(),
)


def adapter_for_runtime(
    runtime_type: str, adapters: tuple[RuntimeAdapter, ...] = DEFAULT_RUNTIME_ADAPTERS
) -> RuntimeAdapter | None:
    normalized = runtime_type.strip().upper().replace("-", "_")
    normalized = {
        "GENERIC": "GENERIC_PROCESS",
        "PROCESS": "GENERIC_PROCESS",
        "NODEJS": "NODE",
        "NODE_JS": "NODE",
        "NODE.JS": "NODE",
    }.get(normalized, normalized)
    return next(
        (
            adapter
            for adapter in adapters
            if adapter.runtime_type.upper().replace("-", "_") == normalized
        ),
        None,
    )


__all__ = [
    "BaseRuntimeAdapter",
    "DEFAULT_RUNTIME_ADAPTERS",
    "DetectionConfidence",
    "GenericProcessRuntimeAdapter",
    "JavaMetadataRuntimeAdapter",
    "NodeRuntimeAdapter",
    "OperationStatus",
    "PhpRuntimeAdapter",
    "PythonRuntimeAdapter",
    "RubyMetadataRuntimeAdapter",
    "RuntimeManifestAdapter",
    "RuntimeAdapter",
    "RuntimeAvailability",
    "RuntimeDescription",
    "RuntimeDetection",
    "RuntimeInstance",
    "RuntimeObservation",
    "RuntimeProbeResult",
    "RuntimeProbeSpec",
    "RuntimeProfileSpec",
    "RuntimeStartResult",
    "RuntimeState",
    "RuntimeStopResult",
    "RuntimeValidation",
    "SafeProcessRunner",
    "adapter_for_runtime",
]
