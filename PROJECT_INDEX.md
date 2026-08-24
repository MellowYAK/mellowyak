# MellowYak project index

Phase 4 source-of-truth pointers:

## Product and policy

- [`README.md`](README.md) — product contract, implemented status and development commands
- [`PRIVACY.md`](PRIVACY.md) — current local data behavior
- [`SECURITY.md`](SECURITY.md) — local process boundary and reporting
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor workflow
- [`docs/OPEN_SOURCE_LICENSE_DECISION.md`](docs/OPEN_SOURCE_LICENSE_DECISION.md) — unresolved license comparison
- [`docs/RELEASES_AND_UPDATES.md`](docs/RELEASES_AND_UPDATES.md) — installer, updater signing and local macOS installation contract
- [`docs/ui-review/phase-3-2026-08-24/PHASE_3_SUMMARY.md`](docs/ui-review/phase-3-2026-08-24/PHASE_3_SUMMARY.md) — Phase 3 summary, APC extraction record, UI screenshots and PDF review index

## Architecture and migration

- [`docs/architecture/ADR-0001-local-first-desktop.md`](docs/architecture/ADR-0001-local-first-desktop.md)
- [`docs/architecture/ADR-0002-local-process-security.md`](docs/architecture/ADR-0002-local-process-security.md)
- [`docs/architecture/ADR-0003-apc-extraction-policy.md`](docs/architecture/ADR-0003-apc-extraction-policy.md)
- [`docs/architecture/ADR-0006-reverse-impact-analysis.md`](docs/architecture/ADR-0006-reverse-impact-analysis.md)
- [`docs/architecture/ADR-0007-context-receipt.md`](docs/architecture/ADR-0007-context-receipt.md)
- [`docs/architecture/ADR-0008-behavior-candidate-foundation.md`](docs/architecture/ADR-0008-behavior-candidate-foundation.md)
- [`docs/architecture/ADR-0009-protected-behavior-versioning.md`](docs/architecture/ADR-0009-protected-behavior-versioning.md)
- [`docs/architecture/ADR-0010-evidence-store-and-lineage.md`](docs/architecture/ADR-0010-evidence-store-and-lineage.md)
- [`docs/architecture/ADR-0011-local-browser-runtime.md`](docs/architecture/ADR-0011-local-browser-runtime.md)
- [`docs/architecture/ADR-0012-browser-capture-privacy.md`](docs/architecture/ADR-0012-browser-capture-privacy.md)
- [`docs/migration/APC_TO_MELLOWYAK_MATRIX.md`](docs/migration/APC_TO_MELLOWYAK_MATRIX.md)
- [`docs/migration/APC_EXTRACTION_BOUNDARY.md`](docs/migration/APC_EXTRACTION_BOUNDARY.md)
- [`docs/migration/PHASE_3_APC_IMPACT_CONTEXT_EXTRACTION.md`](docs/migration/PHASE_3_APC_IMPACT_CONTEXT_EXTRACTION.md)
- [`docs/migration/PHASE_4_APC_BEHAVIOR_BROWSER_EVIDENCE_EXTRACTION.md`](docs/migration/PHASE_4_APC_BEHAVIOR_BROWSER_EVIDENCE_EXTRACTION.md)

## Working entry points

- Engine executable: [`engine/src/mellowyak_engine/main.py`](engine/src/mellowyak_engine/main.py)
- Local API: [`engine/src/mellowyak_engine/api/app.py`](engine/src/mellowyak_engine/api/app.py)
- Database layer: [`engine/src/mellowyak_engine/db/database.py`](engine/src/mellowyak_engine/db/database.py)
- Initial migration: [`engine/alembic/versions/0001_local_core.py`](engine/alembic/versions/0001_local_core.py)
- Project/Git/Impact migration: [`engine/alembic/versions/0002_project_git_impact.py`](engine/alembic/versions/0002_project_git_impact.py)
- Reverse-impact/context migration: [`engine/alembic/versions/0003_reverse_impact_context.py`](engine/alembic/versions/0003_reverse_impact_context.py)
- Behavior/evidence/browser migration: [`engine/alembic/versions/0004_behavior_evidence_browser.py`](engine/alembic/versions/0004_behavior_evidence_browser.py)
- Behavior lifecycle: [`engine/src/mellowyak_engine/behaviors/`](engine/src/mellowyak_engine/behaviors/)
- Evidence store and lineage: [`engine/src/mellowyak_engine/evidence/`](engine/src/mellowyak_engine/evidence/)
- Browser capture arm: [`engine/src/mellowyak_engine/browser/`](engine/src/mellowyak_engine/browser/)
- PulsePlan fixture: [`fixtures/pulseplan/`](fixtures/pulseplan/)
- Project service: [`engine/src/mellowyak_engine/projects/service.py`](engine/src/mellowyak_engine/projects/service.py)
- Git observer: [`engine/src/mellowyak_engine/git/observer.py`](engine/src/mellowyak_engine/git/observer.py)
- Source scan and Impact graph: [`engine/src/mellowyak_engine/scanning/service.py`](engine/src/mellowyak_engine/scanning/service.py)
- Reverse-impact and Context Receipt: [`engine/src/mellowyak_engine/impact/`](engine/src/mellowyak_engine/impact/)
- Passive monitoring: [`engine/src/mellowyak_engine/monitoring/service.py`](engine/src/mellowyak_engine/monitoring/service.py)
- React UI: [`apps/desktop/src/App.tsx`](apps/desktop/src/App.tsx)
- Protected Behaviors UI: [`apps/desktop/src/BehaviorsScreen.tsx`](apps/desktop/src/BehaviorsScreen.tsx)
- English/Hebrew translation keys and RTL policy: [`apps/desktop/src/i18n.ts`](apps/desktop/src/i18n.ts)
- Typed mascot asset mapping: [`apps/desktop/src/mascots.ts`](apps/desktop/src/mascots.ts)
- Mascot asset and UI placement contract: [`assets/mascot/manifest/mascot-usage.md`](assets/mascot/manifest/mascot-usage.md)
- Authoritative startup UI and frame player: [`apps/desktop/src/StartupAnimation.tsx`](apps/desktop/src/StartupAnimation.tsx)
- Startup sprite source/extraction contract: [`assets/mascot/loading/README.md`](assets/mascot/loading/README.md)
- Typed API bridge: [`apps/desktop/src/api.ts`](apps/desktop/src/api.ts)
- Tauri process manager: [`apps/desktop/src-tauri/src/lib.rs`](apps/desktop/src-tauri/src/lib.rs)
- OpenAPI contract: [`packages/contracts/openapi.json`](packages/contracts/openapi.json)

## Tests and packaging

- Engine tests: [`engine/tests/`](engine/tests/)
- Desktop tests: [`apps/desktop/src/App.test.tsx`](apps/desktop/src/App.test.tsx)
- Sidecar builder: [`scripts/build_engine.py`](scripts/build_engine.py)
- Packaged Phase 3 fixture validator: [`scripts/validate_packaged_phase3.py`](scripts/validate_packaged_phase3.py)
- Packaged Phase 4 fixture validator: [`scripts/validate_packaged_phase4.py`](scripts/validate_packaged_phase4.py)
- Browser staging: [`scripts/stage_browser.py`](scripts/stage_browser.py)
- UI translation-key policy check: [`scripts/check_ui_translation_keys.py`](scripts/check_ui_translation_keys.py)
- Deterministic mascot sheet extractor: [`scripts/extract_mascot_sheet.py`](scripts/extract_mascot_sheet.py)
- Deterministic startup sheet extractor: [`scripts/extract_loading_sprite.py`](scripts/extract_loading_sprite.py)
- Cross-platform developer commands: [`scripts/dev.py`](scripts/dev.py)
- Quality workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- Unpublished package matrix: [`.github/workflows/package-smoke.yml`](.github/workflows/package-smoke.yml)
- Commit-aligned macOS/Windows builds: [`.github/workflows/desktop-build.yml`](.github/workflows/desktop-build.yml)
- Phase 1 evidence: [`docs/validation/PHASE_1_LOCAL_CORE_VALIDATION_REPORT.md`](docs/validation/PHASE_1_LOCAL_CORE_VALIDATION_REPORT.md)
- Phase 2 evidence: [`docs/validation/PHASE_2_PROJECT_GIT_IMPACT_VALIDATION_REPORT.md`](docs/validation/PHASE_2_PROJECT_GIT_IMPACT_VALIDATION_REPORT.md)
- Phase 3 execution plan: [`docs/implementation/PHASE_3_EXECUTION_PLAN.md`](docs/implementation/PHASE_3_EXECUTION_PLAN.md)
- Phase 3 evidence: [`docs/validation/PHASE_3_REVERSE_IMPACT_CONTEXT_VALIDATION_REPORT.md`](docs/validation/PHASE_3_REVERSE_IMPACT_CONTEXT_VALIDATION_REPORT.md)
- Phase 4 execution plan: [`docs/implementation/PHASE_4_EXECUTION_PLAN.md`](docs/implementation/PHASE_4_EXECUTION_PLAN.md)
- Phase 4 evidence: [`docs/validation/PHASE_4_BEHAVIOR_EVIDENCE_BROWSER_VALIDATION_REPORT.md`](docs/validation/PHASE_4_BEHAVIOR_EVIDENCE_BROWSER_VALIDATION_REPORT.md)
- Phase 4 Hebrew summary: [`docs/validation/PHASE_4_SUMMARY_HE.md`](docs/validation/PHASE_4_SUMMARY_HE.md)
- Phase 4 UI review map: [`docs/ui-review/PHASE_4_UI_SCREENS.md`](docs/ui-review/PHASE_4_UI_SCREENS.md)

Phase 4 adds human-reviewed browser evidence and revision-bound Last Known Good lineage. It does not perform fresh verification, PASS/FAIL decisions, regression detection, required-check selection, Completion Gate, Repair Context, connector execution, or cloud support.
