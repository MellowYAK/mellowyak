# Phase 4 Execution Plan — Protected Behaviors, Evidence Lineage, and Browser Capture

Date: 2026-08-24

Branch: `product/behavior-evidence-browser-foundation`
Base: `3a4a945788fcf908f1560fc3adb8c79e7e2dd317`

## Outcome

Phase 4 adds a local-only, review-first workflow that turns a behavior draft into an explicitly protected behavior backed by immutable, content-addressed browser evidence. It does not claim test pass/fail, regression detection, automatic healing, or Phase 5 enforcement.

## Safety boundaries

- MellowYak is the only writable repository.
- APC is inspected read-only and contributes concepts, not coupled code, paths, credentials, sessions, or deployment assumptions.
- Browser capture accepts only explicit-port loopback HTTP origins.
- Browser contexts are ephemeral. Cookies, authorization headers, storage state, request bodies, and form values are never persisted.
- Evidence is written atomically, verified by SHA-256, deduplicated, bounded, and deleted only when no accepted baseline references it.
- User review is mandatory before a baseline can be accepted and attached to a protected behavior.
- All visible UI copy comes from English and Hebrew translation catalogs; Hebrew uses full RTL.

## Implementation order

1. Add migration `0004_behavior_evidence_browser` and database models for immutable behavior versions, runtime configurations, captures, observations, artifacts, bundles, attestations, baselines, and audit events.
2. Add local services for behavior lifecycle, content-addressed evidence storage, evidence lineage, and browser capture lifecycle.
3. Add authenticated loopback API contracts and OpenAPI output, including safe evidence deletion and recovery after restart.
4. Add a deterministic local PulsePlan fixture and Playwright capture path with origin/network restrictions, redaction, bounded screenshots, and process cleanup.
5. Add desktop workflows for behavior drafts, runtime configuration, capture, review, acceptance, evidence details, archive, and Impact-to-draft creation.
6. Add English/Hebrew translation keys, complete RTL behavior, and translation-key validation.
7. Add backend, frontend, migration, restart, security, evidence, fixture, and packaged-runtime tests.
8. Update architecture, privacy, security, contribution, extraction, migration, API, packaging, update, and validation documentation.
9. Build and inspect the macOS application and DMG, run packaged Phase 4 validation, record exact evidence, and create one local commit. Do not push or publish.

## Validation gates

- Clean migration from Phase 3 and migration on an existing database.
- Immutable version history and explicit lifecycle transitions.
- Candidate preparation creates a draft only.
- External origins and implicit ports are rejected.
- No secret-bearing browser data is stored or returned.
- Artifact tampering is detected; duplicate content is reused; referenced accepted evidence cannot be deleted.
- Capture survives engine restart as a reviewable interrupted/stale record without losing immutable artifacts.
- English and Hebrew UI tests pass, including RTL and no-hardcoded-text checks.
- PulsePlan exercises capture, review, baseline acceptance, change context, and evidence lookup with no PASS/FAIL claim.
- Packaged app launches its sidecar and packaged browser capture path without developer Python or repository fallback.

## Completion rule

Phase 4 is complete only when implementation, tests, documentation, packaged validation, and the local commit all agree. If a packaged browser cannot be shipped and validated reliably, the phase is reported as partial and is not represented as complete.
