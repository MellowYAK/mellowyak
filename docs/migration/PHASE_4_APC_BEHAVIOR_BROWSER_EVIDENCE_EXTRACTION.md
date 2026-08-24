# Phase 4 APC behavior/browser/evidence extraction

Date: 2026-08-24. APC was inspected read-only. No APC code, credentials, sessions, data, PHP request handling, MariaDB access, Bridge transport, tenancy, or deployment topology was copied.

| APC path | APC status | Decision | Concept reused | MellowYak destination | Security review and proof |
|---|---|---|---|---|---|
| `api/browser-runtime.php`; `tools/browser_runtime/apc_browser_runtime.py`; `tools/browser_runtime/apc_browser_action.py` | VERIFIED_WORKING / coupled | REWRITE | explicit runtime lifecycle, meaningful actions, cleanup | `engine/src/mellowyak_engine/browser/service.py` | exact loopback origin, ephemeral context, shutdown and Playwright fixture tests |
| `inc/browser_runtime_security.php`; `data/browser-runtime/security-policy.json` | VERIFIED_WORKING | PORT | deny-by-default destination policy | browser route guard and runtime URL validator | external origins, implicit ports, credentials, fragments rejected |
| `data/browser-runtime/artifact-retention-policy.json`; `reports/browser-runtime/artifact-retention-report.json` | PARTIAL | REFERENCE_ONLY | bounded local evidence and retention | `engine/src/mellowyak_engine/evidence/` | atomic/hash/dedupe/corruption/size/symlink tests |
| `api/project-map-hybrid-snapshot.php`; `inc/project_map_hybrid_snapshot.php` | PARTIAL / coupled | REWRITE | runtime/source facts remain separately proven | behavior links with explicit provenance | no function-level runtime claim; bodies and headers excluded |
| `inc/screenshot_memory.php`; `data/screenshot-memory.json` | FOUNDATION_ONLY | REFERENCE_ONLY | content identity and local references | content-addressed store | no APC screenshots or data copied; user review required |
| `inc/context/known_good.php`; `api/verified-capabilities.php`; `tools/record_verified_capability.php` | PARTIAL | PORT | immutable lineage, revocation, exact source identity | behavior versions, baselines, attestations and audit events | “Last Known Good” is revision-bound and never a fresh PASS claim |
| `inc/project_source_history.php` | PARTIAL | REFERENCE_ONLY | immutable historical identity | behavior/baseline history | no restore logic enters Phase 4 |
| `_codex_read.php`; `model_context.php`; `api/model.php`; `api/ingest.php` | unsafe legacy boundary | SECURITY_BLOCKER | none | none | DO_NOT_USE: broad source/context and installation-wide authorization are incompatible |
| APC accounts, tenant/user tables, cookies, runtime credentials, Bridge/server routes | legacy/coupled | DO_NOT_USE | none | none | local single-install engine keeps per-launch bearer authentication |

All implementation is a clean Python/React rewrite against MellowYak contracts. APC remains unchanged.
