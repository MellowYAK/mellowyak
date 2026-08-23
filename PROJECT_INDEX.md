# MellowYak project index

Phase 2 source-of-truth pointers:

## Product and policy

- [`README.md`](README.md) — product contract, implemented status and development commands
- [`PRIVACY.md`](PRIVACY.md) — current local data behavior
- [`SECURITY.md`](SECURITY.md) — local process boundary and reporting
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor workflow
- [`docs/OPEN_SOURCE_LICENSE_DECISION.md`](docs/OPEN_SOURCE_LICENSE_DECISION.md) — unresolved license comparison

## Architecture and migration

- [`docs/architecture/ADR-0001-local-first-desktop.md`](docs/architecture/ADR-0001-local-first-desktop.md)
- [`docs/architecture/ADR-0002-local-process-security.md`](docs/architecture/ADR-0002-local-process-security.md)
- [`docs/architecture/ADR-0003-apc-extraction-policy.md`](docs/architecture/ADR-0003-apc-extraction-policy.md)
- [`docs/migration/APC_TO_MELLOWYAK_MATRIX.md`](docs/migration/APC_TO_MELLOWYAK_MATRIX.md)
- [`docs/migration/APC_EXTRACTION_BOUNDARY.md`](docs/migration/APC_EXTRACTION_BOUNDARY.md)

## Working entry points

- Engine executable: [`engine/src/mellowyak_engine/main.py`](engine/src/mellowyak_engine/main.py)
- Local API: [`engine/src/mellowyak_engine/api/app.py`](engine/src/mellowyak_engine/api/app.py)
- Database layer: [`engine/src/mellowyak_engine/db/database.py`](engine/src/mellowyak_engine/db/database.py)
- Initial migration: [`engine/alembic/versions/0001_local_core.py`](engine/alembic/versions/0001_local_core.py)
- Project/Git/Impact migration: [`engine/alembic/versions/0002_project_git_impact.py`](engine/alembic/versions/0002_project_git_impact.py)
- Project service: [`engine/src/mellowyak_engine/projects/service.py`](engine/src/mellowyak_engine/projects/service.py)
- Git observer: [`engine/src/mellowyak_engine/git/observer.py`](engine/src/mellowyak_engine/git/observer.py)
- Source scan and Impact graph: [`engine/src/mellowyak_engine/scanning/service.py`](engine/src/mellowyak_engine/scanning/service.py)
- Passive monitoring: [`engine/src/mellowyak_engine/monitoring/service.py`](engine/src/mellowyak_engine/monitoring/service.py)
- React UI: [`apps/desktop/src/App.tsx`](apps/desktop/src/App.tsx)
- Typed API bridge: [`apps/desktop/src/api.ts`](apps/desktop/src/api.ts)
- Tauri process manager: [`apps/desktop/src-tauri/src/lib.rs`](apps/desktop/src-tauri/src/lib.rs)
- OpenAPI contract: [`packages/contracts/openapi.json`](packages/contracts/openapi.json)

## Tests and packaging

- Engine tests: [`engine/tests/`](engine/tests/)
- Desktop tests: [`apps/desktop/src/App.test.tsx`](apps/desktop/src/App.test.tsx)
- Sidecar builder: [`scripts/build_engine.py`](scripts/build_engine.py)
- Cross-platform developer commands: [`scripts/dev.py`](scripts/dev.py)
- Quality workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- Unpublished package matrix: [`.github/workflows/package-smoke.yml`](.github/workflows/package-smoke.yml)
- Commit-aligned macOS/Windows builds: [`.github/workflows/desktop-build.yml`](.github/workflows/desktop-build.yml)
- Phase 1 evidence: [`docs/validation/PHASE_1_LOCAL_CORE_VALIDATION_REPORT.md`](docs/validation/PHASE_1_LOCAL_CORE_VALIDATION_REPORT.md)
- Phase 2 evidence: [`docs/validation/PHASE_2_PROJECT_GIT_IMPACT_VALIDATION_REPORT.md`](docs/validation/PHASE_2_PROJECT_GIT_IMPACT_VALIDATION_REPORT.md)

Phase 2 provides direct, deterministic relationship foundations only. No listed module should be interpreted as complete impact analysis, regression protection, behavior verification, connector execution, or cloud support.
