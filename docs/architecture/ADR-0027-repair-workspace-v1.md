# ADR-0027 — Read-only-isolated Repair Workspace v1

Status: Accepted — 2026-08-24

## Context

A confirmed regression needs focused, reproducible repair material without risking the live project.
Phase 7 is not an automatic repair, patch application, rollback, or coding-agent integration phase.

## Decision

For an exact confirmed incident, MellowYak may create a project-scoped Repair Workspace beneath its
local data root and outside the live source tree. The workspace contains:

```text
MELLOWYAK_REPAIR.md
incident.json
source-manifest.json
validation-plan.json
current/
evidence/
references/
```

`current/` is a verified materialization of the selected current source snapshot. It contains only
snapshot-included files; ignored, sensitive, provider-private, oversized, and escaping-symlink
content remains absent. JSON and Markdown metadata use relative references, bounded evidence, and
redaction. The manifest digest and database record make the workspace auditable and deletable.

The repair instructions explain KEEP, RESTORE, the current failure, Last Known Good, relevant paths
and symbols when known, required rechecks, unknowns, and two non-negotiable rules: do not blindly
restore old files and do not modify the live project.

The product may reveal/open the workspace locally and delete it. It does not send it to any provider,
run a coding agent, generate a patch, apply changes, copy changes back, modify the live project, or
claim that materialization repairs anything.

## Security invariants

- The workspace path is generated and confined beneath the project’s MellowYak data root.
- Snapshot integrity is verified before materialization.
- Cross-project regression, snapshot, signal, and workspace access is rejected.
- Secret-shaped data and absolute user paths are excluded from instructions/evidence.
- Deletion targets only the resolved MellowYak-owned workspace.

## Consequences

Users can inspect or manually open a stable repair copy in Finder, Explorer, a terminal, or an editor
without risking source overwrite. Validated apply, safety snapshots before apply, hash preconditions,
post-apply verification, and rollback belong to Phase 8.
