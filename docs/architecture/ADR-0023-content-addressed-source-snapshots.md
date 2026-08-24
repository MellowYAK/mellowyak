# ADR-0023 — Content-addressed incremental source snapshots

Status: Accepted — 2026-08-24

## Context

MellowYak needs exact local source identities and recoverable Save Points even when a project does
not use Git. Copying the complete tree after every settled change would waste storage, while storing
source contents in SQLite would mix content, metadata, and retention concerns.

## Decision

Phase 7 stores source content outside the live project and outside SQLite in a project-scoped SHA-256
content-addressed store beneath the MellowYak data root. SQLite stores snapshot, entry, object,
reference, milestone, incident, and repair-workspace metadata only.

Objects and canonical JSON manifests are written to same-directory temporary files, flushed, and
atomically published. A manifest is deterministic: entries and exclusions are normalized and sorted;
JSON keys and separators are canonical; non-finite values are rejected. Loading verifies the manifest
digest and every referenced object digest before materialization.

Snapshot capture:

- confines traversal to the selected project root;
- applies `.gitignore`, `.mellowyakignore`, generated/artifact, sensitive-file, provider-private,
  binary-size, and maximum-object rules;
- records exclusions and counts instead of silently omitting unsupported input;
- never follows a symlink outside the root;
- never recursively captures MellowYak-owned data;
- supports bounded binary files and file-mode/executable metadata;
- creates no new physical object for a digest already present.

The manifest binds the snapshot to its parent, Episode, creation reason, Source Identity v2, optional
Git anchor, and runtime-profile fingerprints. If a settled Episode produces the same entry manifest
as the previous state, MellowYak retains the Episode and reuses the previous snapshot.

Materialization always targets a new MellowYak-owned folder outside the live project. It refuses a
live-tree destination, verifies every object before writing, and never modifies the selected source
folder.

## Retention

The default Beta policy is 30 days and a 5 GiB soft cap per project, both configurable. Cleanup is
reference-safe: pinned known-good milestones, active baselines, incidents, repair workspaces, current
history, and any other live reference protect their snapshots and objects. Collection uses a
mark-and-sweep equivalent and deletes an object only after no retained reference remains.

## Consequences

Logical snapshot size can be much larger than newly stored physical bytes. Corruption is detectable,
but this store is local memory rather than a user backup or cloud synchronization service. Ignored,
sensitive, escaping, and oversized content is intentionally not reproducible from a Save Point and
must remain visible as a limitation.
