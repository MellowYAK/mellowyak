# Phase 3 APC impact/context extraction

Date: 2026-08-24

APC was inspected read-only. No APC source, credentials, tenant data, deployment state or database content was copied into MellowYak. Phase 3 uses clean local-first implementations informed by reviewed concepts.

## Reviewed concepts and disposition

| APC concept | Representative APC source | Decision | MellowYak result |
|---|---|---|---|
| Project MAP correlations | `inc/project_map.php`, `inc/project_map_worker.php`, `inc/project_map_runs.php` | REWRITE | Typed, project-scoped graph traversal with provenance, scan revision and explicit staleness. |
| Source-map-first selection | `inc/context/play_integration.php`, `docs/APC_PLAY_SOURCE_MAP_FIRST_VALIDATION_REPORT.md` | PORT policy only | Bounded deterministic selection and explicit fallback/unknown reasons. No APC code copied. |
| Source map and context routing | `inc/ops.php`, `inc/context/context_router.php`, `inc/context/session_delta_planner.php` | REFERENCE_ONLY | Model-neutral Context Receipt metadata with zero source bytes in Phase 3. |
| Verified-capability lineage | `inc/verified_capabilities.php`, `inc/context/known_good.php` | REFERENCE_ONLY | Revision/provenance vocabulary only. No verification or Last Known Good implementation. |
| Restore and completion contracts | `inc/project_map_backup.php`, `inc/context/capsule_builder.php` | REFERENCE_ONLY | Exact identity and idempotent records influenced design; restore/completion are absent. |
| PHP queues, tenant UI and task control plane | APC `api/`, `inc/`, root PHP screens | DO_NOT_USE | No server control plane, accounts, tenant roles, queue delivery or APC UI. |
| Broad source/context routes | `_codex_read.php`, `model_context.php`, installation-token semantics in `api/model.php` and `api/ingest.php` | SECURITY_BLOCKER / DO_NOT_USE | No equivalent route. Narrow project/change APIs require per-launch local authentication. |

## Clean-room boundary

The implemented code is Python/TypeScript in MellowYak and follows MellowYak schemas, tests and privacy constraints. APC remains a separate server-era product. Runtime adapters, browser capture, connectors, verification, restore and Completion Gate concepts remain outside Phase 3.

## Security outcome

- no source-reading context endpoint;
- no persisted source content in Phase 3 tables;
- no APC credentials or installation-wide token;
- no network client or connector;
- unknown and stale facts cannot silently become authoritative;
- every impact query is project-scoped.

