from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HumanAttestationAdapter:
    """Normalize an explicit local human decision without inventing automation."""

    name: str = "HUMAN_ATTESTATION"
    version: str = "human-attestation-v1"

    RESULTS = {
        "WORKS": "HUMAN_ATTESTED_PASS",
        "DOES_NOT_WORK": "FAIL",
        "UNABLE_TO_VERIFY": "INCONCLUSIVE",
        "UNABLE_TO_DETERMINE": "INCONCLUSIVE",
    }

    def availability(self) -> tuple[bool, None]:
        return True, None

    def normalize(self, result: str, confirmed: bool, note: str) -> str:
        normalized = result.upper().strip()
        if not confirmed or normalized not in self.RESULTS or not note.strip():
            raise ValueError("HUMAN_ATTESTATION_INVALID")
        return self.RESULTS[normalized]
