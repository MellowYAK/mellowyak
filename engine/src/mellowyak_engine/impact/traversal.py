from __future__ import annotations

import time
from collections import defaultdict, deque

from mellowyak_engine.impact.explain import explain_path, reason_for_step
from mellowyak_engine.impact.models import (
    EdgeFact,
    NodeFact,
    PathStep,
    TraversalOutcome,
    TraversalPolicy,
    TraversalResult,
)

EDGE_POLICY = {
    "IMPORTS": "TRANSITIVE_SAFE",
    "INCLUDES": "TRANSITIVE_SAFE",
    "DECLARES": "DIRECT",
    "REFERENCES": "TRANSITIVE_SAFE",
    "TESTS": "TRANSITIVE_SAFE",
    "ROUTE_HINT": "HEURISTIC_BOUNDARY",
    "CONTAINS": "DIRECT",
    "UNKNOWN_RELATION": "STOP",
}
PROVENANCE_STRENGTH = {
    "STATIC_EXACT": 5,
    "STATIC_PARSED": 4,
    "RUNTIME_OBSERVED": 4,
    "MANUAL_APPROVED": 4,
    "STATIC_HEURISTIC": 2,
    "UNKNOWN": 0,
}


def _impact_class(depth: int, heuristic: bool, unknown: bool, stale: bool) -> str:
    if stale:
        return "STALE_RELATION"
    if unknown:
        return "UNKNOWN_BOUNDARY"
    if heuristic:
        return "HEURISTICALLY_RELATED"
    return "DIRECTLY_RELATED" if depth == 1 else "TRANSITIVELY_RELATED"


def traverse(
    nodes: list[NodeFact],
    edges: list[EdgeFact],
    changed_node_ids: list[str],
    policy: TraversalPolicy | None = None,
) -> TraversalOutcome:
    bounded = (policy or TraversalPolicy()).bounded()
    started = time.monotonic()
    by_id = {node.id: node for node in nodes}
    adjacency: dict[str, list[tuple[EdgeFact, str, str]]] = defaultdict(list)
    for edge in edges:
        if edge.edge_type not in EDGE_POLICY:
            continue
        adjacency[edge.source_node_id].append((edge, edge.target_node_id, "outbound"))
        adjacency[edge.target_node_id].append((edge, edge.source_node_id, "inbound"))
    for values in adjacency.values():
        values.sort(key=lambda item: (item[0].edge_type, item[1], item[2], item[0].id))

    results: dict[str, TraversalResult] = {}
    queue: deque[tuple[str, int, list[PathStep], int]] = deque()
    for node_id in sorted(set(changed_node_ids)):
        node = by_id.get(node_id)
        if node is None:
            continue
        results[node_id] = TraversalResult(
            node=node,
            impact_class="CHANGED",
            minimum_depth=0,
            strongest_provenance="CHANGED_FILE",
            stale=False,
            unknown=False,
            explanation=f"{node.label} is one of the exact changed files.",
            paths=[[]],
        )
        queue.append((node_id, 0, [], 0))

    truncation_reasons: list[str] = []
    unknown_count = 0
    explanation_bytes = sum(len(item.explanation.encode()) for item in results.values())
    visited_best: dict[tuple[str, int], int] = {}

    while queue:
        if (time.monotonic() - started) * 1000 > bounded.max_duration_ms:
            truncation_reasons.append("maximum wall-clock analysis time reached")
            break
        current_id, depth, current_path, heuristic_depth = queue.popleft()
        if depth >= bounded.max_depth:
            if adjacency.get(current_id):
                truncation_reasons.append("maximum traversal depth reached")
            continue
        source = by_id.get(current_id)
        if source is None:
            continue
        for edge, neighbor_id, direction in adjacency.get(current_id, []):
            neighbor = by_id.get(neighbor_id)
            if neighbor is None:
                continue
            mode = EDGE_POLICY[edge.edge_type]
            edge_heuristic = edge.provenance == "STATIC_HEURISTIC" or mode == "HEURISTIC_BOUNDARY"
            next_heuristic_depth = heuristic_depth + (1 if edge_heuristic else 0)
            is_unknown = (
                edge.edge_type == "UNKNOWN_RELATION" or neighbor.node_type == "UNKNOWN_REFERENCE"
            )
            is_stale = edge.stale or neighbor.stale
            if is_unknown and unknown_count >= bounded.max_unknown_expansion:
                truncation_reasons.append("maximum unknown expansion reached")
                continue
            if edge_heuristic and next_heuristic_depth > bounded.max_heuristic_depth:
                truncation_reasons.append("maximum heuristic depth reached")
                continue
            next_depth = depth + 1
            reason = reason_for_step(source, neighbor, edge.edge_type, direction, edge.provenance)
            step = PathStep(
                source_node_id=source.id,
                source_label=source.label,
                destination_node_id=neighbor.id,
                destination_label=neighbor.label,
                edge_type=edge.edge_type,
                direction=direction,
                provenance=edge.provenance,
                adapter=edge.adapter,
                scan_revision=edge.scan_revision,
                stale=is_stale,
                depth=next_depth,
                reason_included=reason,
            )
            path = [*current_path, step]
            impact_class = _impact_class(
                next_depth, bool(next_heuristic_depth), is_unknown, is_stale
            )
            unknown_reason = None
            if is_unknown:
                unknown_count += 1
                unknown_reason = (
                    f"Unresolved relation at {neighbor.relative_path or neighbor.label}."
                )
            elif is_stale:
                unknown_reason = (
                    "Relationship belongs to a stale scan revision and was not traversed "
                    "as fresh authority."
                )
            explanation = explain_path(neighbor, path, impact_class)
            encoded_size = len(explanation.encode())
            if explanation_bytes + encoded_size > bounded.max_explanation_bytes:
                truncation_reasons.append("maximum explanation payload reached")
                continue
            existing = results.get(neighbor.id)
            if existing is None:
                if len(results) >= bounded.max_result_nodes:
                    truncation_reasons.append("maximum result nodes reached")
                    queue.clear()
                    break
                existing = TraversalResult(
                    node=neighbor,
                    impact_class=impact_class,
                    minimum_depth=next_depth,
                    strongest_provenance=edge.provenance,
                    stale=is_stale,
                    unknown=is_unknown,
                    explanation=explanation,
                    unknown_reason=unknown_reason,
                    paths=[path],
                )
                results[neighbor.id] = existing
                explanation_bytes += encoded_size
            else:
                if next_depth < existing.minimum_depth:
                    existing.minimum_depth = next_depth
                    existing.impact_class = impact_class
                    existing.explanation = explanation
                    existing.paths = [path]
                elif (
                    len(existing.paths) < bounded.max_paths_per_result
                    and path not in existing.paths
                ):
                    existing.paths.append(path)
                if PROVENANCE_STRENGTH.get(edge.provenance, 1) > PROVENANCE_STRENGTH.get(
                    existing.strongest_provenance, 1
                ):
                    existing.strongest_provenance = edge.provenance
                existing.stale = existing.stale or is_stale
                existing.unknown = existing.unknown or is_unknown
                existing.unknown_reason = existing.unknown_reason or unknown_reason

            stop = mode in {"DIRECT", "HEURISTIC_BOUNDARY", "STOP"} or is_unknown or is_stale
            state = (neighbor.id, next_heuristic_depth)
            if not stop and next_depth < visited_best.get(state, bounded.max_depth + 1):
                visited_best[state] = next_depth
                queue.append((neighbor.id, next_depth, path, next_heuristic_depth))

    ordered = sorted(
        results.values(),
        key=lambda item: (
            item.minimum_depth,
            item.impact_class,
            item.node.relative_path or item.node.label,
            item.node.id,
        ),
    )
    return TraversalOutcome(
        results=ordered,
        truncated=bool(truncation_reasons),
        truncation_reasons=sorted(set(truncation_reasons)),
        duration_ms=round((time.monotonic() - started) * 1000, 3),
    )
