# MellowYak project index

Phase 7 source-of-truth pointers:

## Product and policy

- [`README.md`](README.md) — product contract, implemented status and development commands
- [`PRIVACY.md`](PRIVACY.md) — current local data behavior
- [`SECURITY.md`](SECURITY.md) — local process boundary and reporting
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contributor workflow
- [`docs/OPEN_SOURCE_LICENSE_DECISION.md`](docs/OPEN_SOURCE_LICENSE_DECISION.md) — unresolved license comparison
- [`docs/RELEASES_AND_UPDATES.md`](docs/RELEASES_AND_UPDATES.md) — installer, updater signing and local macOS installation contract
- [`docs/ui-review/phase-3-2026-08-24/PHASE_3_SUMMARY.md`](docs/ui-review/phase-3-2026-08-24/PHASE_3_SUMMARY.md) — Phase 3 summary, APC extraction record, UI screenshots and PDF review index
- [`docs/phase-7-delivery/README.md`](docs/phase-7-delivery/README.md) — portable Phase 7 implementation, verification, screenshot, APC, and research handoff
- [`docs/product/RUNTIME_PROFILE_GUIDE.md`](docs/product/RUNTIME_PROFILE_GUIDE.md) — Runtime Wizard and profile usage
- [`docs/product/SAVE_POINTS_AND_KNOWN_GOOD.md`](docs/product/SAVE_POINTS_AND_KNOWN_GOOD.md) — Episodes, incremental Save Points, milestones, materialization, and retention
- [`docs/product/PROBE_TYPES.md`](docs/product/PROBE_TYPES.md) — Browser/API/CLI/Process/Test/Manual Probe contract and signals

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
- [`docs/architecture/ADR-0013-protection-plan-selection.md`](docs/architecture/ADR-0013-protection-plan-selection.md)
- [`docs/architecture/ADR-0014-verification-adapters.md`](docs/architecture/ADR-0014-verification-adapters.md)
- [`docs/architecture/ADR-0015-regression-decision.md`](docs/architecture/ADR-0015-regression-decision.md)
- [`docs/architecture/ADR-0016-completion-gate.md`](docs/architecture/ADR-0016-completion-gate.md)
- [`docs/architecture/ADR-0017-repair-context.md`](docs/architecture/ADR-0017-repair-context.md)
- [`docs/architecture/ADR-0022-runtime-profile-model.md`](docs/architecture/ADR-0022-runtime-profile-model.md)
- [`docs/architecture/ADR-0023-content-addressed-source-snapshots.md`](docs/architecture/ADR-0023-content-addressed-source-snapshots.md)
- [`docs/architecture/ADR-0024-episode-grouping.md`](docs/architecture/ADR-0024-episode-grouping.md)
- [`docs/architecture/ADR-0025-universal-probe-contract.md`](docs/architecture/ADR-0025-universal-probe-contract.md)
- [`docs/architecture/ADR-0026-source-identity-without-git.md`](docs/architecture/ADR-0026-source-identity-without-git.md)
- [`docs/architecture/ADR-0027-repair-workspace-v1.md`](docs/architecture/ADR-0027-repair-workspace-v1.md)
- [`docs/migration/APC_TO_MELLOWYAK_MATRIX.md`](docs/migration/APC_TO_MELLOWYAK_MATRIX.md)
- [`docs/migration/APC_EXTRACTION_BOUNDARY.md`](docs/migration/APC_EXTRACTION_BOUNDARY.md)
- [`docs/migration/PHASE_3_APC_IMPACT_CONTEXT_EXTRACTION.md`](docs/migration/PHASE_3_APC_IMPACT_CONTEXT_EXTRACTION.md)
- [`docs/migration/PHASE_4_APC_BEHAVIOR_BROWSER_EVIDENCE_EXTRACTION.md`](docs/migration/PHASE_4_APC_BEHAVIOR_BROWSER_EVIDENCE_EXTRACTION.md)
- [`docs/migration/PHASE_5_APC_VERIFICATION_GATE_REPAIR_EXTRACTION.md`](docs/migration/PHASE_5_APC_VERIFICATION_GATE_REPAIR_EXTRACTION.md)

## Working entry points

- Engine executable: [`engine/src/mellowyak_engine/main.py`](engine/src/mellowyak_engine/main.py)
- Local API: [`engine/src/mellowyak_engine/api/app.py`](engine/src/mellowyak_engine/api/app.py)
- Database layer: [`engine/src/mellowyak_engine/db/database.py`](engine/src/mellowyak_engine/db/database.py)
- Initial migration: [`engine/alembic/versions/0001_local_core.py`](engine/alembic/versions/0001_local_core.py)
- Project/Git/Impact migration: [`engine/alembic/versions/0002_project_git_impact.py`](engine/alembic/versions/0002_project_git_impact.py)
- Reverse-impact/context migration: [`engine/alembic/versions/0003_reverse_impact_context.py`](engine/alembic/versions/0003_reverse_impact_context.py)
- Behavior/evidence/browser migration: [`engine/alembic/versions/0004_behavior_evidence_browser.py`](engine/alembic/versions/0004_behavior_evidence_browser.py)
- Verification/regression/gate migration: [`engine/alembic/versions/0005_verification_regression_gate.py`](engine/alembic/versions/0005_verification_regression_gate.py)
- Desktop productization migration: [`engine/alembic/versions/0006_desktop_productization.py`](engine/alembic/versions/0006_desktop_productization.py)
- Runtime/snapshot/probe migration: [`engine/alembic/versions/0007_runtime_snapshot_probe_foundation.py`](engine/alembic/versions/0007_runtime_snapshot_probe_foundation.py)
- Protection Plan selection: [`engine/src/mellowyak_engine/protection/`](engine/src/mellowyak_engine/protection/)
- Verification adapters and assertions: [`engine/src/mellowyak_engine/verification/`](engine/src/mellowyak_engine/verification/)
- Regression decisions: [`engine/src/mellowyak_engine/regression/`](engine/src/mellowyak_engine/regression/)
- Completion Gate: [`engine/src/mellowyak_engine/gate/`](engine/src/mellowyak_engine/gate/)
- Repair Context: [`engine/src/mellowyak_engine/repair/`](engine/src/mellowyak_engine/repair/)
- Behavior lifecycle: [`engine/src/mellowyak_engine/behaviors/`](engine/src/mellowyak_engine/behaviors/)
- Evidence store and lineage: [`engine/src/mellowyak_engine/evidence/`](engine/src/mellowyak_engine/evidence/)
- Browser capture arm: [`engine/src/mellowyak_engine/browser/`](engine/src/mellowyak_engine/browser/)
- PulsePlan fixture: [`fixtures/pulseplan/`](fixtures/pulseplan/)
- Project service: [`engine/src/mellowyak_engine/projects/service.py`](engine/src/mellowyak_engine/projects/service.py)
- Git observer: [`engine/src/mellowyak_engine/git/observer.py`](engine/src/mellowyak_engine/git/observer.py)
- Source scan and Impact graph: [`engine/src/mellowyak_engine/scanning/service.py`](engine/src/mellowyak_engine/scanning/service.py)
- Reverse-impact and Context Receipt: [`engine/src/mellowyak_engine/impact/`](engine/src/mellowyak_engine/impact/)
- Passive monitoring: [`engine/src/mellowyak_engine/monitoring/service.py`](engine/src/mellowyak_engine/monitoring/service.py)
- Source Identity v2: [`engine/src/mellowyak_engine/source_identity.py`](engine/src/mellowyak_engine/source_identity.py)
- Runtime Profile service and detection: [`engine/src/mellowyak_engine/runtime_profiles/`](engine/src/mellowyak_engine/runtime_profiles/)
- Runtime adapter registry/contracts: [`engine/src/mellowyak_engine/runtime_adapters/`](engine/src/mellowyak_engine/runtime_adapters/)
- Episode grouping: [`engine/src/mellowyak_engine/episodes/`](engine/src/mellowyak_engine/episodes/)
- Snapshot CAS/service/materialization: [`engine/src/mellowyak_engine/snapshots/`](engine/src/mellowyak_engine/snapshots/)
- Universal Probe service/adapters/signals: [`engine/src/mellowyak_engine/probes/`](engine/src/mellowyak_engine/probes/)
- Repair Workspace v1: [`engine/src/mellowyak_engine/repair_workspace/`](engine/src/mellowyak_engine/repair_workspace/)
- React UI: [`apps/desktop/src/App.tsx`](apps/desktop/src/App.tsx)
- Change Cockpit: [`apps/desktop/src/ChangeCockpit.tsx`](apps/desktop/src/ChangeCockpit.tsx)
- Protected Behaviors UI: [`apps/desktop/src/BehaviorsScreen.tsx`](apps/desktop/src/BehaviorsScreen.tsx)
- Runtime Wizard: [`apps/desktop/src/RuntimeWizard.tsx`](apps/desktop/src/RuntimeWizard.tsx)
- Runtime screen: [`apps/desktop/src/RuntimeScreen.tsx`](apps/desktop/src/RuntimeScreen.tsx)
- Memory/Save Points screen: [`apps/desktop/src/MemoryScreen.tsx`](apps/desktop/src/MemoryScreen.tsx)
- Universal Probe panel: [`apps/desktop/src/ProbePanel.tsx`](apps/desktop/src/ProbePanel.tsx)
- Ready-with-limits, signal, and Repair Workspace UI: [`apps/desktop/src/Phase7Details.tsx`](apps/desktop/src/Phase7Details.tsx)
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
- Packaged Phase 5 regression/repair validator: [`scripts/validate_packaged_phase5.py`](scripts/validate_packaged_phase5.py)
- Packaged Phase 7 non-Git/probe/repair validator: [`scripts/validate_packaged_phase7.py`](scripts/validate_packaged_phase7.py)
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
- Phase 5 execution plan: [`docs/implementation/PHASE_5_EXECUTION_PLAN.md`](docs/implementation/PHASE_5_EXECUTION_PLAN.md)
- Phase 5 validation: [`docs/validation/PHASE_5_VERIFICATION_REGRESSION_GATE_VALIDATION_REPORT.md`](docs/validation/PHASE_5_VERIFICATION_REGRESSION_GATE_VALIDATION_REPORT.md)
- Phase 5 Hebrew summary: [`docs/validation/PHASE_5_SUMMARY_HE.md`](docs/validation/PHASE_5_SUMMARY_HE.md)
- Phase 5 UI screen map: [`docs/ui/PHASE_5_UI_SCREENS.md`](docs/ui/PHASE_5_UI_SCREENS.md)
- Phase 6 execution plan: [`docs/implementation/PHASE_6_EXECUTION_PLAN.md`](docs/implementation/PHASE_6_EXECUTION_PLAN.md)
- Phase 6 portable delivery: [`docs/phase-6-desktop-productization-2026-08-24/README.md`](docs/phase-6-desktop-productization-2026-08-24/README.md)
- Phase 7 execution plan: [`docs/implementation/PHASE_7_EXECUTION_PLAN.md`](docs/implementation/PHASE_7_EXECUTION_PLAN.md)
- Phase 7 technical sources: [`docs/research/PHASE_7_TECHNICAL_SOURCES.md`](docs/research/PHASE_7_TECHNICAL_SOURCES.md)
- Phase 7 validation: [`docs/validation/PHASE_7_RUNTIME_MEMORY_PROBE_VALIDATION_REPORT.md`](docs/validation/PHASE_7_RUNTIME_MEMORY_PROBE_VALIDATION_REPORT.md)
- Phase 7 current UI map: [`docs/ui/PHASE_7_UI_SCREENS.md`](docs/ui/PHASE_7_UI_SCREENS.md)

Phase 7 adds Git-optional Source Identity, versioned Runtime Profiles, incremental Save Points,
Episodes, universal local Probes, known-good milestones, deterministic evidence signals, and isolated
Repair Workspaces. It does not add coding-agent integration, prompt/provider-token access, cloud
upload, automatic repair/apply, deployment/rollback, signing, notarization, or public release.
