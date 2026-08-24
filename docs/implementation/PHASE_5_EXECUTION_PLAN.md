# Phase 5 execution plan — selective verification, regression gate, and repair context

Date: 2026-08-24

Branch: `product/verification-regression-gate`

Base: `408375978194c48180e5cc1c0885031dcaaf7b7b`

## Bounded implementation plan

1. Add migration `0005_verification_regression_gate` and concrete immutable records for protection plans/items, verification runs/items/assertions, human attestations, regression findings, gate decisions, repair contexts, reverification links, and audit events. Preserve migrations `0001` through `0004` unchanged.
2. Build a deterministic Protection Plan selector. Exact current FILE/SYMBOL, runtime-observed parsed, bounded parsed-transitive, stale, heuristic, unknown, no-relation, and `always_recheck` inputs map to explicit classes and reason paths. Plans bind Change, HEAD, worktree fingerprint, scan, impact, behavior versions, baselines, algorithm, and policy; changed identities make them stale.
3. Add typed verification adapters. Browser Replay uses a new ephemeral, loopback-confined Chromium context and the accepted capture steps; Human Attestation is explicit and labeled. A general command adapter remains interface-only unless its shell-free package gate passes.
4. Execute deterministic URL, element, text, attribute, API-call, and HTTP-status assertions. Screenshot references require review and human notes never pass automatically. Store fresh verification bundles separately from immutable baseline evidence.
5. Add regression comparison, immutable local Completion Gate decisions, source-change invalidation, deterministic `mellowyak.repair_context.v1`, and reverification lineage. Only assertion failures that satisfy the complete accepted-baseline contract become regressions.
6. Add authenticated project-scoped APIs/events and a translation-key-only Change Cockpit for plan, runner, Last Known Good versus Current, regression, repair context, timeline, and gate. English remains the base catalog and Hebrew remains full RTL.
7. Extend PulsePlan with deterministic regression and repair states, add unit/API/UI/security/migration/restart tests, generate deterministic OpenAPI/TypeScript contracts, and retain every Phase 1–4 test.
8. Build the Python sidecar, macOS app and DMG; mount/inspect the DMG; run the packaged regression → blocked gate → repair context → new source state → reverification → verified-complete flow; record hashes/timing and create one local commit without push or release.

## Contracts and cut line

Limits: 250 plan items, 50 required, 100 suggested, browser concurrency 2, 120 seconds per behavior, 15 minutes per run, 100 assertions per behavior, 250 MiB current evidence, and 256 KiB Repair Context/copy payload.

Phase 5 does not generate repairs, replace Last Known Good automatically, call a model, run arbitrary shell commands, connect to Codex/Claude/Cursor/MCP, block Git/CI, add accounts/cloud/analytics, sign, notarize, publish, or claim complete blast-radius knowledge. Phase 6 does not begin in this change.
