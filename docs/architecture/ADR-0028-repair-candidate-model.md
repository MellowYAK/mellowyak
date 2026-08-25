# ADR-0028: Repair candidate model

Status: Accepted — 2026-08-25

## Decision

A repair candidate is an immutable, revisioned comparison between a Repair Workspace base manifest and its current bounded tree. The canonical manifest records relative paths, ADD/MODIFY/DELETE/RENAME/MODE_CHANGE operations, hashes, sizes, modes, classification, eligibility, exclusions, warnings, and limitations. Source bytes never enter SQLite.

The scanner is independent of Git and is limited to 250 files, 64 MiB total, 10 MiB per file, a 1 MiB preview, and 4,000 diff lines. Symlinks, hard links, special files, path escape, case collision, sensitive paths, and provider-private directories are rejected. Exact-digest rename detection is permitted; uncertainty remains DELETE plus ADD.

## Consequences

Every workspace edit creates a new candidate revision or makes prior validation stale. The model is deterministic and usable by Git and non-Git projects, while binary changes remain visible but are not automatically apply-eligible.
