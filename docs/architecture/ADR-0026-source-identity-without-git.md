# ADR-0026 — Source Identity v2 with optional Git

Status: Accepted — 2026-08-24

## Context

Previous MellowYak phases used Git HEAD and worktree fingerprints as the primary change identity.
Projects without `.git` still need stable scans, snapshots, milestones, probes, comparisons, and
repair workspaces without teaching users commit vocabulary.

## Decision

Source Identity v2 is a typed union with two compatible forms:

1. Git-backed identity: HEAD, branch/ref, worktree fingerprint, snapshot ID, and manifest digest.
2. Snapshot-backed identity: parent snapshot, current snapshot, manifest digest, and Episode ID.

Git-backed projects keep their existing identity and gain the snapshot anchor. Non-Git projects use
the deterministic manifest digest and lineage. The UI calls these states `Save Point`, `Change
Episode`, and `Current working state`; Git details are optional advanced evidence.

Migration `0007_runtime_snapshot_probe_foundation` does not delete or rewrite any existing Change,
Impact, behavior, baseline, evidence, regression, gate, alert, or preference record. A new snapshot
can create or map to an existing `ProjectChange` so the established Impact and Protection Plan path
remains authoritative.

Comparability requires exact relevant identity fields, not merely a matching project or file name.
Probe runs and milestones persist their exact snapshot and Runtime Profile versions. A different
manifest, stale runtime profile, unsupported boundary, or missing accepted baseline is surfaced and
cannot silently inherit a prior PASS.

## Consequences

Git is an optional evidence source, not a product prerequisite. Snapshot identity describes source
content that MellowYak included; it does not claim knowledge of excluded or sensitive files. Existing
Git history remains readable and valid, while non-Git users receive the complete local Phase 7 flow.
