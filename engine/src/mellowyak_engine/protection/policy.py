from __future__ import annotations

MAX_PLAN_ITEMS = 250
MAX_REQUIRED_CHECKS = 50
MAX_SUGGESTED_CHECKS = 100
ALGORITHM_VERSION = "protection-selection-v1"
POLICY_VERSION = "local-default-v1"

PARSED_PROVENANCE = frozenset({"STATIC_PARSED", "EXACT_PARSER", "RUNTIME_OBSERVED_PARSED"})
HEURISTIC_PROVENANCE = frozenset({"STATIC_HEURISTIC", "HEURISTIC"})

SKIPPED_REASON = "No current known relation selected this behavior."
