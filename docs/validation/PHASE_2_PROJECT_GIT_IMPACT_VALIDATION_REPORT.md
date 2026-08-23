# Phase 2 Project, Git, Source Scan, and Impact validation

- Date: 2026-08-23
- Scope: Phase 2 local foundations only
- Result: implementation verified locally; package and remote CI results recorded separately

## Implemented

- Native Tauri directory picker and real project detection UI.
- SQLite-persisted projects, Git snapshots, change observations, scans, files, findings, impact nodes, and impact edges through migration `0002_project_git_impact`.
- Read-only Dulwich Git state for repository root, branch, HEAD, detached/dirty status, staged, unstaged, untracked, and a deterministic worktree fingerprint.
- Bounded scanning with Git/MellowYak ignore rules, default build/cache exclusions, sensitive metadata-only handling, binary and oversized exclusions, and escaping-symlink rejection.
- Deterministic relationship adapters for Python and conservative JavaScript, TypeScript, TSX, and PHP parsing. Each edge records provenance and adapter identity; unresolved references remain explicit unknown nodes.
- Initial full scan, persisted progress, cancellation, rerun, stale relationship handling, impact summary/search, findings, event polling, and passive debounced monitoring with polling fallback.
- Honest UI states: Ready, Ready with limits, Scan incomplete, Git unavailable, and explicit unknown/unsupported counts.
- Exact-commit macOS and Windows build workflow. Artifacts and an immutable commit manifest are uploaded without publishing a release or committing binaries.

## Privacy and security evidence

The engine remains loopback-only and every application endpoint requires the per-launch bearer token. Project source is read from the selected canonical root. Source contents are not stored in SQLite, logs, events, or project metadata. The integration test writes a unique secret to sensitive, ignored, and outside-root files and verifies that the byte sequence is absent from every file under the MellowYak data root after scanning and restart.

The scanner does not follow escaping symlinks. Git observation does not invoke checkout, reset, add, commit, fetch, push, or any repository mutation. No cloud, analytics, account, source-upload, or outbound client was added.

## Local validation

The final validation command set covers:

- 20 Python engine/API/security/persistence/Git/scan/impact tests;
- Ruff lint and formatting;
- React native-picker, local status, and detection tests;
- TypeScript typecheck and production Vite build;
- generated OpenAPI contract;
- Rust formatting/checks;
- managed sidecar build and macOS application/DMG packaging.

Final macOS package gate:

- `.app`: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
- `.dmg`: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg`
- DMG SHA-256: `df82783f7a93a3cce5ddaa90e23ec0c92cbb0e5d83c8d594340b788c788a87a1`
- desktop executable SHA-256: `2db2d1b1ef98568627eb4c1d29ccf875c64e074c714f8cc0237748a8f3be6cde`
- bundled engine SHA-256: `668fc657431c3b5c608c9b392e3060d044f38de6888febcd1bb93b01ceba87d6`

The read-only DMG mount contains both executables. The packaged engine produced the expected local handshake, listened on a dynamic IPv4 loopback port, migrated a temporary database to `0002_project_git_impact`, and returned authenticated health with database ready, cloud disconnected, and outbound network disabled. PyInstaller cold startup took longer than the first ten-second probe; the bounded fifty-second package probe completed successfully.

The first clean-checkout GitHub Actions run correctly exposed two workflow-only path gaps: the quality job invoked the engine builder relative to the Rust working directory, and the desktop matrix did not regenerate the intentionally ignored typed OpenAPI client. Both workflows now generate the local contract explicitly and use repository-root paths. Those failed attempts are retained in Actions history and are not relabeled as successful evidence.

## Explicit limits

- Phase 2 relationships are direct static foundations, not a complete blast radius.
- Windows runtime packaging is executed by CI, not claimed as locally verified on macOS.
- Signing, notarization, automatic updates, Protected Behaviors, runtime evidence, regression verification, Completion Gate, repair context, and APC connector execution remain future work.
- APC is an optional future project-scoped API integration. No APC source or server dependency is included in MellowYak.
