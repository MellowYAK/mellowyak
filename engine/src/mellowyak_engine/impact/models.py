from __future__ import annotations

from dataclasses import asdict, dataclass, field

ALGORITHM_VERSION = "reverse-impact-v1"


@dataclass(frozen=True)
class TraversalPolicy:
    max_depth: int = 4
    max_result_nodes: int = 250
    max_paths_per_result: int = 3
    max_heuristic_depth: int = 1
    max_duration_ms: int = 1_500
    max_unknown_expansion: int = 50
    max_explanation_bytes: int = 48_000

    def bounded(self) -> TraversalPolicy:
        return TraversalPolicy(
            max_depth=min(max(self.max_depth, 1), 8),
            max_result_nodes=min(max(self.max_result_nodes, 1), 2_000),
            max_paths_per_result=min(max(self.max_paths_per_result, 1), 10),
            max_heuristic_depth=min(max(self.max_heuristic_depth, 0), 2),
            max_duration_ms=min(max(self.max_duration_ms, 10), 10_000),
            max_unknown_expansion=min(max(self.max_unknown_expansion, 0), 250),
            max_explanation_bytes=min(max(self.max_explanation_bytes, 1_024), 256_000),
        )

    def public_dict(self) -> dict[str, int]:
        return asdict(self.bounded())


@dataclass(frozen=True)
class NodeFact:
    id: str
    node_type: str
    label: str
    relative_path: str | None
    stale: bool = False


@dataclass(frozen=True)
class EdgeFact:
    id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    provenance: str
    adapter: str
    scan_revision: str
    stale: bool = False


@dataclass(frozen=True)
class PathStep:
    source_node_id: str
    source_label: str
    destination_node_id: str
    destination_label: str
    edge_type: str
    direction: str
    provenance: str
    adapter: str
    scan_revision: str
    stale: bool
    depth: int
    reason_included: str

    def public_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class TraversalResult:
    node: NodeFact
    impact_class: str
    minimum_depth: int
    strongest_provenance: str
    stale: bool
    unknown: bool
    explanation: str
    unknown_reason: str | None = None
    paths: list[list[PathStep]] = field(default_factory=list)
    ranking_score: float = 0.0
    ranking_reasons: list[str] = field(default_factory=list)


@dataclass
class TraversalOutcome:
    results: list[TraversalResult]
    truncated: bool
    truncation_reasons: list[str]
    duration_ms: float
