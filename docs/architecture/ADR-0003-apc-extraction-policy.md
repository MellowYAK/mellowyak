# ADR-0003: APC extraction policy

- Status: Accepted
- Date: 2026-08-23

## Decision

APC is read-only source material and is not copied wholesale. Capability status is assigned from reproducible runtime, active source/configuration, persistent evidence, tests, Git history and current reports—in that order. A route, card, schema or historical claim does not prove a capability.

Verified contracts, isolated algorithms, test fixtures and documented lessons may later be ported when the migration matrix permits it. Server deployment code, PHP pages, MariaDB/Docker topology, tenancy, generated artifacts and old UI are rejected. Rewrites target MellowYak's local typed interfaces instead of preserving APC boundaries.

Every future APC-derived fragment needs a provenance record containing exact source path, original status, migration decision, security review, destination and covering tests. `_codex_read.php`, `model_context.php`, and installation-token-wide `api/model.php` / `api/ingest.php` semantics are security blocked and cannot be reused.

## Consequences

Migration takes longer than bulk copying but avoids importing unsupported claims and security debt. Phase 1 deliberately contains no APC product feature; the matrix and boundary document are the only extraction outputs.
