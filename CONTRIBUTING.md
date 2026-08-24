# Contributing

Phase 7 changes must preserve the central evidence law: a changed file, dependency, or Impact path is
only a reason to recheck and cannot create a regression claim. `CONFIRMED` requires comparable
accepted PASS evidence followed by reproducible current FAIL evidence, or the existing independently
supported regression decision.

Runtime and Probe changes must keep executable and argv separate, use no shell, confine working
directories to the project, inherit only a minimal safe environment, default network access to
loopback, bound output/time, support cancellation, and clean up owned children. Detection must not
install dependencies or execute package scripts without explicit approval.

Snapshot and Repair Workspace changes must preserve project/data-root confinement, deterministic
SHA-256 manifests, atomic writes, sensitive/provider-private exclusions, symlink safety, integrity
verification, deduplication, reference-safe retention, and live-source immutability. Never commit
snapshot objects/manifests, materialized copies, databases, evidence, Repair Workspaces, runtime
events/logs, user paths, provider data, or generated installers.

Before proposing Phase 7 changes, run the complete Python and React suites, translation checker,
TypeScript/Vite, Ruff check/format, Cargo format/check, deterministic OpenAPI export and TypeScript
generation, the full migration matrix, packaged-engine smoke, and relevant packaged Phase 7 flows.
Use final artifact data only in validation documentation; do not reuse old package hashes or replace a
pending field with an unrun success claim.

All visible React text—including labels, placeholders, accessible names, and mascot descriptions—must
come from translation keys. English is the base catalog, Hebrew must have exact parity and RTL, and
`python3 scripts/check_ui_translation_keys.py` is mandatory.

Phase 5 changes must run the PulsePlan baseline, seeded regression, Repair Context, repaired re-verification and restart-history flows; all migration, evidence integrity/privacy, gate, UI translation-key, English/Hebrew RTL, packaged sidecar and packaged browser checks; and `scripts/validate_packaged_phase5.py` against the built app engine. Never commit local evidence, Repair Context output, captured screenshots/traces/video, browser profiles, Playwright cache, generated installers, private updater keys, source fixtures copied from user projects, or APC data. Browser changes must preserve exact loopback-origin enforcement and must not persist headers, bodies, cookies, storage state, or input values.

Phase 1 protects a strict local-first boundary. Do not add cloud endpoints, telemetry upload, accounts, Docker, APC server code, or a Phase 2 feature under a placeholder claim.

## Development prerequisites

Contributors need Python 3.12, Node.js 22+, Rust stable and platform prerequisites for Tauri 2. End users do not need these because the packaged application bundles its engine and frontend.

```sh
python3 scripts/dev.py bootstrap
python3 scripts/dev.py test
python3 scripts/dev.py lint
python3 scripts/dev.py typecheck
python3 scripts/dev.py engine-build
python3 scripts/dev.py desktop-build
python3 scripts/dev.py package
```

Run `python3 scripts/dev.py clean` only to remove generated build outputs. Update `packages/contracts/openapi.json` with `python3 scripts/export_openapi.py`, then regenerate TypeScript types with `npm run contract:generate` from `apps/desktop` whenever the API changes.

Before proposing a change, run all checks, inspect `git diff --check`, avoid absolute user paths/secrets/generated binaries, and update the relevant validation evidence. APC-derived work must follow ADR-0003 and record provenance.
