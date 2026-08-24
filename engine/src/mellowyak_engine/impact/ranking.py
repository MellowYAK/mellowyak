from __future__ import annotations

import re
from pathlib import PurePosixPath

from mellowyak_engine.impact.models import TraversalResult

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")


def tokens(value: str | None) -> set[str]:
    return {item.casefold() for item in TOKEN_PATTERN.findall(value or "") if len(item) >= 2}


def rank_result(
    result: TraversalResult, task_intent: str | None, changed_paths: set[str]
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if result.impact_class == "CHANGED":
        score += 100
        reasons.append("exact changed file")
    distance_score = max(0, 40 - result.minimum_depth * 8)
    score += distance_score
    reasons.append(f"distance {result.minimum_depth} from changed source")
    if result.strongest_provenance in {"STATIC_EXACT", "STATIC_PARSED"}:
        score += 30
        reasons.append("exact or parsed static relationship")
    elif result.strongest_provenance == "STATIC_HEURISTIC":
        score -= 10
        reasons.append("heuristic relationship penalty")
    if result.node.node_type == "TEST":
        score += 25
        reasons.append("test relationship")
    intent_tokens = tokens(task_intent)
    node_tokens = tokens(" ".join(filter(None, [result.node.label, result.node.relative_path])))
    overlap = sorted(intent_tokens & node_tokens)
    if overlap:
        score += min(24, len(overlap) * 8)
        reasons.append("intent token overlap: " + ", ".join(overlap[:4]))
    path = result.node.relative_path or ""
    parent = str(PurePosixPath(path).parent) if path else ""
    if parent and any(str(PurePosixPath(item).parent) == parent for item in changed_paths):
        score += 8
        reasons.append("same directory as a changed file")
    if result.stale:
        score -= 35
        reasons.append("stale relationship penalty")
    if result.unknown:
        score -= 20
        reasons.append("unknown boundary")
    return score, reasons
