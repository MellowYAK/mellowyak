# ADR-0006: bounded reverse-impact analysis

- Status: Accepted
- Date: 2026-08-24
- Algorithm: `reverse-impact-v1`

## Context

Phase 2 stores project-local file, test and relationship facts with provenance and scan revision. Phase 3 needs to answer which known entities may relate to exact changed files without claiming a complete blast radius.

## Decision

A `Change` is the stable analysis root. A clean repository uses `base HEAD → current HEAD`; a dirty repository uses `HEAD + deterministic worktree fingerprint`. Analysis begins only from changed file/test nodes in the latest completed scan.

Traversal is deterministic and bidirectional only for an explicit relation policy. Defaults are bounded by depth, result count, paths per result, explanation bytes and heuristic depth. Parsed relations and heuristic relations have different impact classes and ranking. Unknown and stale relations are visible terminal boundaries; they are never traversed as authoritative facts. Every persisted result is bound to the Change identity, Git revision, scan revision, algorithm version and traversal policy.

Old results remain inspectable but become stale when the Change identity, worktree fingerprint or scan revision changes.

## Consequences

- Results are explainable relationship facts, not probability scores.
- A missing changed node becomes an explicit unknown boundary.
- Bounded output can be truncated and always records why.
- No embeddings, network service, source upload or automatic test execution is involved.
- This does not implement regression detection, verification or Protected Behaviors.

