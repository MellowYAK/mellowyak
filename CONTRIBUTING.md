# Contributing

Phase 4 changes must run the PulsePlan browser fixture, migration tests, evidence integrity/privacy tests, UI translation-key check, English/Hebrew RTL tests, packaged sidecar smoke, and packaged browser flow. Never commit local evidence, captured screenshots/traces/video, browser profiles, Playwright cache, generated installers, private updater keys, source fixtures copied from user projects, or APC data. Browser changes must preserve exact loopback-origin enforcement and must not persist headers, bodies, cookies, storage state, or input values.

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
