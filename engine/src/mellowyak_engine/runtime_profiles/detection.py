from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mellowyak_engine.runtime_adapters import DEFAULT_RUNTIME_ADAPTERS
from mellowyak_engine.runtime_adapters.base import (
    DetectionConfidence,
    RuntimeAdapter,
    RuntimeDetection,
)


@dataclass(frozen=True)
class RuntimeDetectionFailure:
    adapter_name: str
    reason: str


@dataclass(frozen=True)
class RuntimeDetectionReport:
    project_root: str
    detections: tuple[RuntimeDetection, ...]
    failures: tuple[RuntimeDetectionFailure, ...] = ()

    @property
    def ready_with_limits(self) -> bool:
        return bool(self.failures) or any(item.limitations for item in self.detections)


class RuntimeDetectionService:
    def __init__(self, adapters: tuple[RuntimeAdapter, ...] = DEFAULT_RUNTIME_ADAPTERS) -> None:
        self.adapters = adapters

    def detect(self, project: Path) -> RuntimeDetectionReport:
        root = project.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise NotADirectoryError(root)
        detections: list[RuntimeDetection] = []
        failures: list[RuntimeDetectionFailure] = []
        for adapter in self.adapters:
            try:
                detections.extend(adapter.detect(root))
            except Exception:
                # Detection is fail-open: one unavailable runtime cannot block other runtimes.
                failures.append(
                    RuntimeDetectionFailure(
                        adapter_name=adapter.name,
                        reason="runtime.detection.adapter_failed",
                    )
                )
        confidence_rank = {
            DetectionConfidence.HIGH: 0,
            DetectionConfidence.MEDIUM: 1,
            DetectionConfidence.LOW: 2,
        }
        detections.sort(
            key=lambda item: (
                confidence_rank[item.confidence],
                item.runtime_type,
                item.adapter_name,
            )
        )
        failures.sort(key=lambda item: item.adapter_name)
        return RuntimeDetectionReport(
            project_root=str(root),
            detections=tuple(detections),
            failures=tuple(failures),
        )


def detect_project(
    project: Path, adapters: tuple[RuntimeAdapter, ...] = DEFAULT_RUNTIME_ADAPTERS
) -> RuntimeDetectionReport:
    return RuntimeDetectionService(adapters).detect(project)
