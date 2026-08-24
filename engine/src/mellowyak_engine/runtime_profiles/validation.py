from __future__ import annotations

from dataclasses import dataclass

from mellowyak_engine.runtime_adapters import DEFAULT_RUNTIME_ADAPTERS, adapter_for_runtime
from mellowyak_engine.runtime_adapters.base import (
    RuntimeAdapter,
    RuntimeAvailability,
    RuntimeProfileSpec,
    RuntimeValidation,
)


@dataclass(frozen=True)
class ProfileValidationReport:
    adapter_name: str | None
    validation: RuntimeValidation
    availability: RuntimeAvailability | None


def validate_runtime_profile(
    profile: RuntimeProfileSpec,
    adapters: tuple[RuntimeAdapter, ...] = DEFAULT_RUNTIME_ADAPTERS,
) -> ProfileValidationReport:
    adapter = adapter_for_runtime(profile.runtime_type, adapters)
    if adapter is None:
        return ProfileValidationReport(
            adapter_name=None,
            validation=RuntimeValidation(
                valid=False,
                errors=("runtime.validation.adapter_unavailable",),
            ),
            availability=None,
        )
    validation = adapter.validate(profile)
    availability = adapter.availability(profile) if validation.valid else None
    return ProfileValidationReport(
        adapter_name=adapter.name,
        validation=validation,
        availability=availability,
    )
