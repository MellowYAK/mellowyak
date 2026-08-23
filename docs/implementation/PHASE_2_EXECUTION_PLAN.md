# Phase 2 execution plan

Date: 2026-08-23. Cut line: Project, Git, Source Scan, and Impact Foundations only.

## Modules

- `projects`: canonical-path validation, detection, persistence and project summaries.
- `git`: bundled Dulwich read-only state, stable fingerprints and snapshots.
- `scanning`: bounded inventory, ignore/sensitive/binary policy, deterministic parser adapters, progress and cancellation.
- `impact`: persisted nodes/edges, provenance, staleness, summaries and search.
- `monitoring`: project-root-only watchfiles observer with debounce and bounded polling fallback.

## Schema

Alembic `0002_project_git_impact` extends `projects` and adds `project_git_snapshots`, `project_change_observations`, `project_scan_runs`, `project_files`, `impact_nodes`, `impact_edges`, and `scan_findings`. SQLite stores paths, metadata, hashes and bounded parser output—never source contents.

## API and UI

Authenticated project detection/connect/list/detail, scan/start/status/cancel, Git, changes, impact summary/search, monitoring pause/resume, event polling and open-folder APIs. React routes cover First Setup, native-folder Add Project, Projects, Readiness/scan progress, Project Overview and relationship details. Tauri's native dialog plugin is the primary path selector.

## APC references

Read-only concepts are referenced from `inc/project_map.php` (bounded inventory/hash baseline and preview), `inc/project_map_worker.php` (source correlation provenance and explicit gaps), `inc/project_map_task_refresh.php` (stable signatures and changed-file concepts), `inc/ops.php` (Source Map builders/likely-file policy), and current `tests/test_project_map_*` contracts. No APC code is copied; PHP, MariaDB, tenancy, routes, task state and UI are excluded.

## Security boundary

Retain loopback/dynamic-port/per-launch-token/origin security and no outbound clients. Git and scan are read-only, canonical-root confined, do not follow escaping symlinks, protect sensitive content, redact home paths in diagnostics, and never mutate a repository.

## Tests

Programmatic fixture repositories cover clean/dirty/staged/unstaged/untracked/ignored/detached Git, duplicate/path/symlink boundaries, ignore/default/sensitive/binary/large scan policy, deterministic relationships/provenance/unknowns, incremental invalidation/cancellation, debounced observations/restart, API security, UI routes/progress/readiness and packaged smoke.

## Packaging risks and fallback

Dulwich, pathspec and watchfiles must survive PyInstaller. If watchfiles fails in a packaged build, a low-frequency local polling adapter preserves fingerprint debounce. JavaScript/TypeScript/TSX/PHP use conservative scanners marked `STATIC_HEURISTIC`; Python AST is `STATIC_PARSED`. Unsupported relations remain explicit unknowns. No Phase 3 traversal, behavior, verification, regression, connector or runtime feature crosses the cut line.
