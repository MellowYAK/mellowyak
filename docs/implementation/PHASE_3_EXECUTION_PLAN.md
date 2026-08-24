# Phase 3 execution plan

Date: 2026-08-24. Cut line: Reverse Impact, Context Receipt, and Behavior Candidate foundations only.

## Schema changes

Alembic `0003_reverse_impact_context` adds stable project changes, revision-bound impact analyses/inputs/results/paths, deterministic Context Receipts/items, and project-scoped behavior candidates/links. Records contain identities, relative paths, graph facts, reasons, counts, bounds, and hashes—never repository source contents.

## Analysis and traversal

- Derive committed identity from `base HEAD -> head HEAD`, and dirty identity from `HEAD + worktree fingerprint`; reuse identical identities and create a new revision when the fingerprint changes.
- Traverse only allowlisted FILE/TEST/SYMBOL/ROUTE_HINT/DIRECTORY relationships with `DIRECT`, `TRANSITIVE_SAFE`, `HEURISTIC_BOUNDARY`, or `STOP` policy.
- Bound depth, nodes, paths, heuristic depth, wall time, unknown expansion, and explanation bytes. Unknown edges terminate. Stale edges are reported but do not participate as fresh authority.
- Persist deterministic result classes and at least one fact-derived path: `CHANGED`, `DIRECTLY_RELATED`, `TRANSITIVELY_RELATED`, `HEURISTICALLY_RELATED`, `UNKNOWN_BOUNDARY`, or `STALE_RELATION`.

## Context Receipt and intent

Optional local task intent supplies filename/symbol token overlap only; no model, embedding, network, or semantic claim. A model-neutral receipt selects bounded files, symbols, tests, and paths with explicit reasons, provenance, staleness, exclusions, unknowns, and byte metrics. Sensitive content is never eligible; source snippets require an explicit future local request and are absent by default.

## Behavior candidates

Deterministic test/route/component hints create deduplicated project-scoped `CANDIDATE` records. Users may keep, dismiss, or prepare a `PROMOTED_STUB`; none is protected, verified, PASS/FAIL, or Last Known Good.

## API and UI

Authenticated loopback endpoints expose current/change detail, analyze, impact paths/unknowns, optional intent, Context Receipt, behavior actions, and incoming/outgoing Impact Explorer details. The desktop adds Changes and Impact navigation with truthful changed/related/may-depend, unknown/stale, receipt, and candidate copy.

All desktop product copy uses compile-time checked translation keys with complete English and Hebrew catalogs. Hebrew applies document-level RTL while technical paths and JSON remain LTR. Packaged-engine startup is asynchronous: `ENGINE_STARTING` is retried for a bounded interval so a slow PyInstaller cold start cannot abort AppKit setup.

## Tests

Cover stable identities, traversal direction/bounds/provenance/explanations/truncation, stale invalidation, deterministic/budgeted/sensitive-safe receipts, ranking, behavior lifecycle/deduplication, project isolation, API auth/origin, UI sections/copy, migration upgrades, restart persistence, no persisted source, no outbound sockets, packaging, and a medium synthetic graph.

## Phase 3 cut line

No verification execution, Protected Behavior, Browser Runtime, screenshot/trace/video, regression, PASS/FAIL, Completion Gate, repair, connector, MCP, cloud, account, analytics, embedding, signing, notarization, or release publishing is implemented.
