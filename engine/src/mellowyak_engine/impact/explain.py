from __future__ import annotations

from mellowyak_engine.impact.models import NodeFact, PathStep


def relationship_phrase(edge_type: str, direction: str) -> str:
    phrases = {
        "IMPORTS": ("imports", "is imported by"),
        "INCLUDES": ("includes", "is included by"),
        "DECLARES": ("declares", "is declared by"),
        "REFERENCES": ("references", "is referenced by"),
        "TESTS": ("tests", "is tested by"),
        "ROUTE_HINT": ("points to", "has a route hint from"),
        "CONTAINS": ("contains", "is contained by"),
        "UNKNOWN_RELATION": ("has an unresolved reference to", "has an unresolved reference from"),
    }
    pair = phrases.get(edge_type, (edge_type.lower().replace("_", " "), "relates back to"))
    return pair[0] if direction == "outbound" else pair[1]


def reason_for_step(
    source: NodeFact, destination: NodeFact, edge_type: str, direction: str, provenance: str
) -> str:
    phrase = relationship_phrase(edge_type, direction)
    return f"{destination.label} is included because {source.label} {phrase} it ({provenance})."


def explain_path(node: NodeFact, path: list[PathStep], impact_class: str) -> str:
    if not path:
        return f"{node.label} is one of the exact changed files."
    facts = "; then ".join(step.reason_included for step in path)
    labels = {
        "DIRECTLY_RELATED": "directly related",
        "TRANSITIVELY_RELATED": "transitively related",
        "HEURISTICALLY_RELATED": "heuristically related",
        "UNKNOWN_BOUNDARY": "an unknown boundary",
        "STALE_RELATION": "a stale relation",
    }
    return f"{node.label} is {labels.get(impact_class, 'related')}: {facts}"
