# APC to MellowYak migration matrix

Updated: 2026-08-24. The local APC checkout was inspected read-only; paths below are APC-repository-relative. Status labels describe evidence, not aspiration. No APC business logic was copied in Phases 1–3.

| # | APC capability | APC status | Exact APC source paths | Current evidence | Limitations | Security concerns | MellowYak destination | Decision | Reason | Required rewrite | Required tests | Target phase |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Local Bridge | PARTIAL | `tools/local_bridge/apc_local_bridge.py`; `tools/local_bridge/visual_connector_trainer.py`; `inc/bridge_auth.php` | Current source and bridge stability report show useful transport, execution and trainer concepts. | Remains coupled to APC server/client topology. | Prior listeners and server credentials expand attack surface. | `engine/src/mellowyak_engine/` | REWRITE | Local execution belongs inside the managed Local Engine. | Loopback process API, ephemeral auth, supervision. | Bind, auth, lifecycle, no-outbound tests. | 1 foundation; later capabilities |
| 2 | VS Code connector | PARTIAL | `tools/vscode_chat_telemetry/src/vscodeConnector.ts`; `tools/vscode_chat_telemetry/src/extension.ts` | Connector adapters and fixtures exist. | Availability depends on external UI/tool state. | Accessibility permissions and unintended delivery. | Future connector package | REFERENCE_ONLY | Connector is explicitly out of Phase 1. | Consent, capability negotiation, bounded queue. | Permission, destination, retry/idempotency tests. | 4+
| 3 | Codex delivery | PARTIAL | `tools/vscode_chat_telemetry/src/adapters/codex.ts`; `inc/context/universal_delivery.php` | Delivery concepts and telemetry adapter exist. | Not a connector-neutral proven delivery layer. | Prompt/source disclosure and duplicate sends. | Future connector interface | REFERENCE_ONLY | Keep contract lessons only. | User-enabled connector with explicit data boundary. | Consent, payload preview, dedupe tests. | 4+
| 4 | Browser Runtime | VERIFIED_WORKING | `api/browser-runtime.php`; `inc/browser_runtime_security.php`; `data/browser-runtime/security-policy.json`; `reports/browser-runtime/healthcheck-report.json` | Current health/security evidence describes a valuable runtime asset. | APC deployment-specific and excluded now. | Browser automation and artifacts require strict isolation. | Future execution arm | PORT | Reuse verified algorithms/contracts selectively, never the topology. | Local sandboxed worker and retention model. | Runtime isolation, permissions, artifact tests. | 5+
| 5 | Playwright actions | IMPLEMENTED_NOT_RUNTIME_VERIFIED | `api/browser-runtime.php`; `data/browser-runtime/tool-registry.json` | Action registry/source exists. | General action reliability not proven in this extraction. | Arbitrary navigation/input risk. | Future browser execution arm | REWRITE | Preserve action-contract ideas behind consent. | Allowlist, timeouts, sandbox. | Adversarial navigation and action tests. | 5+
| 6 | Browser screenshots, videos, traces | PARTIAL | `data/browser-runtime/artifact-retention-policy.json`; `reports/browser-runtime/artifact-retention-report.json` | Artifact retention work is evidenced. | End-to-end portability not established. | Highly sensitive evidence and path leakage. | Local `evidence/` filesystem | REFERENCE_ONLY | Evidence remains filesystem-local; no feature in Phase 1. | Metadata-only SQLite references, lifecycle policy. | Retention, access, redaction tests. | 5+
| 7 | Hybrid capture | PARTIAL | `api/project-map-hybrid-snapshot.php`; `schemas/project-map-hybrid-snapshot.schema.json` | Schema and endpoint exist. | Not a complete portable recorder. | Screenshots/traces can capture secrets. | Future recorder module | FREEZE | Explicitly excluded until privacy and recorder design. | Local capture with visible consent. | Consent, pause, retention tests. | 5+
| 8 | Project MAP source signatures | PARTIAL | `inc/project_map.php`; `inc/project_map_worker.php`; `api/project-map-runs.php` | Useful source signature foundations exist. | Not a complete impact engine. | Source contents and hashes are sensitive. | Phase 2 local scanner and graph | PORT | Concepts were independently implemented with language adapters, provenance and scan revision; no APC code copied. | Continue adapter coverage without weakening unknown states. | Fixture accuracy, incremental scan tests. | 2 implemented
| 9 | Project MAP source/runtime relationships | PARTIAL | `inc/project_map_runs.php`; `api/project-map-flow.php`; `api/project-map-browser.php` | Source correlation foundations exist; runtime coverage remains unproven. | Complete reverse impact remains unknowable; runtime is absent. | Runtime evidence may expose secrets. | Phase 3 reverse-impact core | REWRITE | Clean typed, bounded static traversal now distinguishes parsed, heuristic, unknown and stale facts. Runtime relationships remain excluded. | Future runtime facts require separate provenance and consent. | Bounds, determinism, staleness, isolation and provenance tests. | 3 static implemented; runtime later
| 10 | PLAY Source Map / likely-files policy | VERIFIED_WORKING | `docs/APC_PLAY_SOURCE_MAP_FIRST_VALIDATION_REPORT.md`; `inc/context/play_integration.php` | Validation supports source-map-first discovery. | Policy is not complete blast-radius knowledge. | Wrong candidates can disclose unrelated files. | Phase 3 Context Receipt selector | PORT | Bounded metadata selection, ranking and disclosure constraints implemented without APC source. | Source snippets remain disabled pending a separate disclosure design. | Ranking, budgets, scope, secret and no-network tests. | 3 implemented metadata only
| 11 | Restore Contract | PARTIAL | `api/project-map-backup.php`; `inc/project_map_backup.php` | Backup/restore concepts exist. | Coupled to APC storage and server operations. | Destructive restore and path traversal. | Future selective restore service | REWRITE | Must be transactional and project-scoped. | Snapshot manifest, dry run, atomic restore. | Traversal, rollback, conflict tests. | 6+
| 12 | Completion/Result Capsule | PARTIAL | `inc/context/capsule_builder.php`; `inc/context/capsule_ir.php`; `api/context/capsule.php` | Exact project/task, idempotency, proof and result ideas are useful. | Current transport remains APC-specific. | Forged or cross-project completion. | Future result contract | PORT | Contract semantics are reusable. | Signed/local provenance and schema versioning. | Idempotency, scope, proof tests. | 4
| 13 | No-Bridge completion import | PARTIAL | `docs/APC_NO_BRIDGE_COMPLETION_SYNC_VALIDATION_REPORT.md`; `inc/context/cognitive_result_lifecycle.php` | Current report validates useful completion-import behavior. | Not yet connector-neutral. | Untrusted imported results. | Future import adapter | REWRITE | Treat all imports as untrusted local inputs. | Validation, quarantine, replay protection. | Malformed, duplicate, cross-project tests. | 4
| 14 | Verified Solution Memory | PARTIAL | `inc/context/known_good.php`; `tools/record_verified_capability.php`; `api/verified-capabilities.php` | Lineage, immutable evidence, last-known-good, hash and versioning concepts exist. | Not a complete executable Behavior Contract. | Poisoned memory and stale proof. | Future verified memory | PORT | Preserve evidence semantics, not claims. | Immutable manifests and revalidation. | Tamper, staleness, lineage tests. | 3+
| 15 | Source history and selective restore | PARTIAL | `inc/project_map_backup.php`; `api/project-map-backup.php` | Selective-history foundations exist. | APC filesystem/database assumptions. | Data loss and restoring outside root. | Future local history store | REWRITE | Needs Git-aware, atomic local semantics. | Content-addressed snapshots and safe restore. | Traversal, atomicity, recovery tests. | 6+
| 16 | Screenshot Memory | FOUNDATION_ONLY | `inc/screenshot_memory.php`; `data/screenshot-memory.json` | Storage structures and proof sidecars exist. | No proven general memory engine. | Visual evidence contains private data. | Future evidence index | FREEZE | Privacy model must come first. | Encrypted/permissioned local metadata design. | Redaction, retention, access tests. | 5+
| 17 | Task proof and evidence | PARTIAL | `apc_reports/`; `inc/context/task_contract.php` | Reports demonstrate proof-oriented records. | Task-centric workflow conflicts with passive-first product. | Evidence authenticity and accidental disclosure. | Future evidence contracts | PORT | Keep proof model without mandatory tasks. | Event/project-scoped evidence manifests. | Integrity, scope, retention tests. | 3+
| 18 | Telemetry | PARTIAL | `assets/what-now-telemetry.js`; `tools/vscode_chat_telemetry/`; `api/context/metrics.php` | Local telemetry code exists. | Some semantics assume centralized APC. | Remote telemetry violates Phase 1 contract. | Local diagnostics only | DO_NOT_USE | No telemetry upload is permitted. | Explicitly local, redacted diagnostic events only. | No-endpoint/no-outbound tests. | 1 local diagnostics
| 19 | Context planner | PARTIAL | `inc/context/session_delta_planner.php`; `inc/context/context_router.php`; `inc/context/obligation_compiler.php` | Planning components exist. | Production quality and savings unverified. | Context can leak source across boundaries. | Future investigation planner | REFERENCE_ONLY | Reassess after local map/evidence foundations. | Bounded project-local planner. | Scope, completeness, privacy tests. | 4+
| 20 | Cognitive optimizer | DOCUMENTED_ONLY | `inc/context/context_optimizer.php`; `api/context/optimizer.php`; `tools/context_optimizer_evidence.php` | Code and evidence scaffolding exist. | Not a proven production token-saving system. | Misleading optimization claims. | None in Phase 1 | FREEZE | Explicit evidence boundary. | Independent benchmark before any port. | Reproducible efficacy and quality tests. | Unscheduled
| 21 | Semantic Codec | FOUNDATION_ONLY | `inc/context/semantic_codec_lab.php`; `inc/context/semantic_codec_api_service.php` | Experimental lab/service files exist. | Not proven production token saving. | Lossy omission and unsupported claims. | None | FREEZE | Must remain experimental. | Formal quality/effectiveness evaluation. | Fidelity and adversarial omission tests. | Unscheduled
| 22 | System Capability Brain | FOUNDATION_ONLY | `inc/verified_capabilities.php`; `verified_capabilities.php` | Capability registry UI/data exists. | Tool/Pattern/Memory/QA sidecars are health shells, not engines. | False capability representation. | Future local capability registry | REFERENCE_ONLY | Only evidence/status vocabulary is reusable. | Evidence-backed capability discovery. | Truthfulness and stale-state tests. | 4+
| 23 | Tenant/user/role system | LEGACY_OR_SUPERSEDED | `api/auth-context.php`; `api/task-auth-context.php` | Server auth context exists. | Unnecessary for one-user local Phase 1. | Cross-tenant and credential complexity. | None | ARCHIVE | Local app needs no account or tenancy. | Optional team-server design only later. | Future isolation tests. | Optional server
| 24 | Storage profiles | PARTIAL | `inc/project_map_scope.php`; `api/project-map-scope.php` | APC storage/scope concepts exist. | Coupled to server paths and tenant model. | Path traversal and overbroad scope. | `engine/.../storage/paths.py` | REWRITE | Platform-native, single-install local roots required. | platformdirs paths and root confinement. | Platform/path traversal tests. | 1
| 25 | System Control | PARTIAL | `system_control.php`; `inc/system_control.php`; `docs/infrastructure/APC_SYSTEM_CONTROL_PANEL.md` | Host-control UI/actions exist. | Server operator product surface, not desktop core. | Privileged host operations. | None | DO_NOT_USE | Violates lightweight least-privilege product. | No rewrite in desktop core. | Absence/permission audit. | Never in core
| 26 | PHP control plane | LEGACY_OR_SUPERSEDED | `index.php`; `api/`; `inc/` | APC runtime uses PHP control-plane code. | Server-centric monolith. | Broad web attack surface. | FastAPI local engine | ARCHIVE | Architecture is intentionally replaced. | Typed local API only. | API auth/origin/bind tests. | 1
| 27 | MariaDB | LEGACY_OR_SUPERSEDED | `inc/db.php`; `sql/` | APC persistent store depends on server database. | Requires external service and oversized schema. | Credentials, network exposure and tenant data. | SQLite/Alembic | ARCHIVE | Single-machine local store is sufficient. | Minimal schema and migrations. | Migration, WAL, recovery tests. | 1
| 28 | Docker deployment | LEGACY_OR_SUPERSEDED | `docker-compose.yml`; `docker/` | Server/browser containers exist. | End user must install no Docker. | Daemon and exposed service surface. | Tauri bundle + sidecar | ARCHIVE | One native application is required. | Native cross-platform packaging. | Clean-machine package smoke tests. | 1+
| 29 | Legacy UI islands | LEGACY_OR_SUPERSEDED | `assets/project-map-studio.js`; `assets/project-map-guided.js`; root `*.php` pages | Multiple APC pages exist. | Fragmented server UI and unrelated product surfaces. | Old routes may expose privileged actions. | React desktop routes | ARCHIVE | New product needs a cohesive truthful UI. | Rebuild only when a capability is migrated. | UI contract and accessibility tests. | Per future phase
| 30 | Unsafe legacy APIs and routes | DISABLED_OR_PROTECTED | `_codex_read.php`; `model_context.php`; `api/model.php`; `api/ingest.php` | Current source documents broad read/context and installation-token semantics. | Incompatible with project-scoped least privilege. | Arbitrary source/context disclosure and installation-wide authorization. | None | SECURITY_BLOCKER | Must never enter MellowYak. | New narrowly scoped APIs only after threat review. | Negative route, auth-scope and exfiltration tests. | Never port

## Interpretation

## Phase 4 update

- Browser Runtime and Playwright actions are now a clean `REWRITE` in the local Python engine with exact loopback-origin enforcement; APC server/browser topology was not copied.
- Browser artifacts, Hybrid capture, Screenshot Memory, Verified Solution Memory, and task-proof concepts informed the independent evidence/lineage contract documented in `PHASE_4_APC_BEHAVIOR_BROWSER_EVIDENCE_EXTRACTION.md`.
- Phase 4 destinations are `engine/.../browser/`, `engine/.../evidence/`, `engine/.../behaviors/`, migration `0004_behavior_evidence_browser`, and `BehaviorsScreen.tsx`.
- APC runtime credentials, accounts, tenants, cookies, Bridge transport, PHP/MariaDB persistence, backup/restore, broad readers, and model/ingest routes remain `DO_NOT_USE` or `SECURITY_BLOCKER`.

## Phase 5 update

- Completion/Result Capsule proof normalization and exact binding informed clean immutable verification/gate records; no APC PHP was copied.
- Verified Solution Memory informed the strict distinction between active Last Known Good and separate current verification evidence.
- Source-history and selective-restore concepts are `REFERENCE_ONLY` or `REWRITE`: MellowYak preserves failure/re-verification lineage and emits Repair Context constraints but performs no restore.
- Browser proof execution is a clean Python `REWRITE` with ephemeral loopback-only replay, deterministic assertions and packaged cleanup validation.
- Phase 5 destinations are `engine/.../protection/`, `verification/`, `regression/`, `gate/`, `repair/`, migration `0005_verification_regression_gate`, and `ChangeCockpit.tsx`.
- APC Bridge, PLAY, queue, tenant, credentials, PHP/MariaDB, broad reader, model, ingest and server deployment code remain excluded or security-blocked.

## Phase 7 update

Phase 7 did not reopen or modify APC. It extends only MellowYak's local architecture.

| Phase 7 capability | APC relationship | MellowYak destination | Disposition | Boundary |
|---|---|---|---|---|
| Multiple Runtime Profiles | General lesson that one project can expose several local execution surfaces | `engine/src/mellowyak_engine/runtime_profiles/`, `runtime_adapters/` | `REWRITE` | No Bridge, account, credential, server process control, or APC runtime code |
| Git-optional Source Identity | Source-history/product lesson only | `engine/src/mellowyak_engine/source_identity.py`, `episodes/` | `REWRITE` | Existing MellowYak Change/Impact records are extended, never replaced by APC history |
| Incremental Save Points | Historical source-memory concept only | `engine/src/mellowyak_engine/snapshots/` | `REWRITE` | New local SHA-256 store; no APC backup/database/storage format or source copying |
| Universal Probes | Browser/evidence lessons already cleanly extracted in Phases 4–5 | `engine/src/mellowyak_engine/probes/` | `REWRITE` | Extends MellowYak Browser Replay/Protection Plan; no PLAY queue, remote agent, or broad executor |
| Repair Workspace v1 | Selective-restore/repair-context lesson only | `engine/src/mellowyak_engine/repair_workspace/` | `REWRITE` | Isolated materialization only; no live-tree restore, automatic apply, or coding-agent integration |
| Runtime/Memory desktop UI | No reusable APC UI | Phase 7 React screens and translation catalogs | `REWRITE` | No APC PHP pages/assets; every visible string remains a translation key |

Migration `0007_runtime_snapshot_probe_foundation` and all Phase 7 tables are MellowYak-native.
APC PHP/MariaDB, tenant/user roles, Docker deployment, Bridge transport, queues, installation-wide
tokens, broad context/model/ingest readers, provider credentials, and server control remain
`ARCHIVE`, `DO_NOT_USE`, or `SECURITY_BLOCKER`.

## Phase 8 update

Phase 8 did not reopen, write to, or copy code from APC. It extends MellowYak's existing local
Repair Workspace, snapshot, verification, regression, Completion Gate, evidence, and alert
contracts as a clean implementation.

| Phase 8 capability | APC relationship | MellowYak destination | Disposition | Boundary |
|---|---|---|---|---|
| Candidate Patch | Historical selective-restore concept only | `engine/src/mellowyak_engine/repair_candidates/` | `REWRITE` | Deterministic workspace comparison; no Git correctness dependency and no source content in SQLite |
| Candidate Validation | Existing MellowYak Probe/Protection Plan architecture | `engine/src/mellowyak_engine/repair_validation/` | `EXTEND` | Runs only in the isolated workspace; workspace PASS never becomes live PASS |
| Safe Apply | No reusable APC implementation | `engine/src/mellowyak_engine/safe_apply/` | `REWRITE` | Explicit, one-time candidate/project/source-bound confirmation and live path re-hashing |
| Transaction Rollback | APC backup/restore remains unsafe for reuse | `engine/src/mellowyak_engine/safe_apply/rollback.py` | `REWRITE` | Reverts only MellowYak's own Apply transaction from its fresh safety snapshot; not general restore |
| Recovery Bundle | General evidence/report lesson only | `engine/src/mellowyak_engine/recovery/` | `REWRITE` | Local redacted metadata for unresolved transaction recovery; no upload |
| Demo Lab / Self-Test | No APC dependency | `engine/src/mellowyak_engine/demo_lab/` | `NEW` | Disposable synthetic projects only; cannot mutate a registered real project |

Migration `0008_validated_repair_apply` and all Phase 8 tables are MellowYak-native. APC Bridge,
queues, coding-agent connections, provider credentials, PHP/MariaDB persistence, Docker topology,
broad source readers, arbitrary historical restore, accounts, and remote transport remain excluded.

- `PORT` means only the independently reviewable concept, contract, algorithm or fixture may later cross the boundary with provenance and tests.
- `REWRITE` means no code copy: implement against MellowYak's local contracts.
- `SECURITY_BLOCKER` overrides all historical evidence and permanently blocks direct reuse.
- Phase 3 adds bounded static reverse impact, explicit unknown/stale boundaries, a metadata-only Context Receipt, and non-verified behavior candidates. It does not add runtime evidence, Protected Behaviors, verification, connectors, Completion Gate, repair automation or cloud support.

## Mandatory security-blocked route disposition

| APC source | Classification | Disposition |
|---|---|---|
| `_codex_read.php` | SECURITY_BLOCKER | DO_NOT_USE |
| `model_context.php` | SECURITY_BLOCKER | DO_NOT_USE |
| installation-token-wide semantics in `api/model.php` | SECURITY_BLOCKER | DO_NOT_USE |
| installation-token-wide semantics in `api/ingest.php` | SECURITY_BLOCKER | DO_NOT_USE |

`SECURITY_BLOCKER` records why the source cannot cross the boundary; `DO_NOT_USE` is its mandatory implementation disposition. Neither status can be relaxed by historical documentation or tests.
