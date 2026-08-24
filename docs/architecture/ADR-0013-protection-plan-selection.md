# ADR-0013 — Deterministic Protection Plan selection

Status: Accepted — 2026-08-24

## Decision

Each exact Change and fresh impact analysis produces a new immutable Protection Plan. Current PROTECTED behaviors are classified as REQUIRED, SUGGESTED, SKIPPED, NEEDS_REVIEW, or UNKNOWN from exact links, parsed paths, heuristic provenance, staleness, unknown boundaries, criticality, and `always_recheck`. A direct exact relation, a current parsed relation, or an explicit sentinel is REQUIRED. A heuristic is SUGGESTED unless a critical boundary requires review. No known relation is SKIPPED and never described as unaffected.

Plans bind Change ID, HEAD, worktree fingerprint, scan revision, impact analysis, behavior versions, baseline IDs, algorithm version, and policy version. Any mismatch makes the plan stale. Limits are 250 items, 50 required, and 100 suggested.

## Consequences

Only REQUIRED items run automatically. Every classification retains a reason and impact path. Unknown stays unknown; no complete blast-radius claim is made.
