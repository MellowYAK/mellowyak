# ADR-0010: Evidence store and lineage

Date: 2026-08-24
Status: Accepted

## Decision

Binary and large evidence stays outside SQLite under the platform data root:

`evidence/<project-id>/objects/<sha-prefix>/<sha256>`

Bundle manifests are deterministic JSON at `evidence/<project-id>/bundles/<bundle-id>/manifest.json`. SQLite stores hashes, sizes, media types, relative local references, capture/behavior/version identity, source/runtime identity, redaction state, trust source, attestations, and audit events.

Writes use same-directory temporary files, `fsync`, atomic replacement, post-write hashing, project bounds, and symlink/traversal rejection. Accepted evidence cannot be removed except through explicit baseline revocation. Duplicate bytes reuse the same project-scoped object.

## Consequences

Evidence survives restart and can be integrity-checked without exposing public URLs or normal-log absolute paths. The store is local and is not an upload mechanism.
