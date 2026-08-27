# MellowYak Phase 15M Operator Manual

This English-only manual explains the final Phase 15M product-lock surfaces and the rest of the MellowYak navigation model. Product localization remains complete in English and Hebrew, and Hebrew renders through the same components in RTL. Screenshots are intentionally English only.

## Screenshot truth and scrolling method

Every screenshot in this manual is a deterministic representation from the final `0.5.0-preview.1` frontend. It is not physical macOS acceptance evidence. Native capture was unavailable because Screen Recording permission was not granted.

The capture viewport is 1440×1000. Each state was opened at the top, captured, scrolled smoothly by a human-sized step, allowed to settle, and captured again at the bottom. `part-01` is the top view; `part-02` is the scrolled view with intentional overlap. No full-page screenshot shortcut was used.

## Global application shell

The top shell is consistent across pages:

- MellowYak icon/name: returns to Home.
- Home: current operational summary and next safe action.
- Projects: registered local projects and project actions.
- Alerts: local actionable notices and safe project-bound destinations.
- Settings: privacy, notification, monitoring, Quiet Mode, activity policy, onboarding replay, diagnostics, and local self-test access.
- Language: switches between English LTR and Hebrew RTL from translation catalogs.
- Update banner: appears only for an eligible signed update; it never implies that the production updater channel exists.

## Complete page inventory

### Startup

Shows real engine, database, capability, project discovery, and final readiness stages. A slow or failed stage remains visible; Ready is never shown before local prerequisites complete. Retry reruns startup. Technical Details exposes sanitized reason codes.

### Home

Answers “What is happening now?” using registered projects, current monitoring state, recent verified activity, and known limitations. Project cards open Project Overview. Add Project opens the native folder selection flow. No-confirmed-issue means no confirmed issue was found in current evidence—not that the whole project is safe.

### Projects

Lists registered projects, readiness, monitoring state, runtime limits, latest activity, and actions. Open enters the project. Project Actions supports safe disconnect/reconnect/pause/mute flows with confirmation. Add Project never uploads source.

### Add Project

Choose Project Folder opens the native local folder picker. The review surface shows display alias, repository identity, Git state when available, detected language/framework/test/runtime hints, candidate/ignored counts, and local-source notice. Connect Project registers the canonical root; Choose Another discards the pending selection.

### Disconnected Projects

Shows projects whose source is unavailable. Reconnect must resolve to the same canonical project identity; Remove/forget affects MellowYak registration only and never deletes project source.

### Project Overview

Summarizes source identity, current Known Good facts, latest checks, storage integrity, recent activity, known facts, and unknowns. Open Activity shows Episodes; project navigation opens Impact, Behaviors, Runtime, Memory, and Repairs.

### Activity

Lists bounded Episodes and orchestration outcomes. Filters/selectors narrow history. Selecting an Episode opens its evidence, check selection, deferrals, results, and receipt eligibility. A settled Episode may create one immutable Yak Receipt.

### Regression Detail

Shows the protected behavior, previous PASS, current repeated comparable failure, retries, source identity, evidence provenance, and honest status. Create Repair Workspace is available only for an eligible confirmed regression; dismiss/review/resolution actions remain explicit.

### Change / Repairs

Shows changed files, selected impact entities, paths, boundaries, context receipt, behavior candidates, known behavior links, and the repair cockpit. Analyze computes bounded impact. Generate/Copy Context Receipt produces source-free focused context. Repair Workspace, candidate validation, review, confirmation, Apply, fresh live recheck, commit, or transaction rollback follow engine state.

### Impact Explorer

Searches the local relationship graph. Results show direction, relationship type, provenance, scan revision, stale boundaries, and recent changes. It does not claim causation or complete coverage.

### Behaviors

Lists protected behaviors, lifecycle, runtime, evidence, Known Good, capture/review controls, and Baseline Lock. Protect/accept requires actual comparable PASS. Phase 15 adds Expected/Regression/Unsure decisions, reverification, deliberate promotion, and immutable lineage.

### Runtime

Shows detected Runtime Profiles, approval state, exact executable/argument boundaries, health checks, allowed ports, secrets warnings, and runtime-unavailable limitations. Setup/Approve is explicit; detected commands do not run automatically.

### Memory

Shows incremental snapshots, Episodes, evidence summaries, storage policy, and Yak Receipts. Create Yak Receipt is available only for a settled eligible Episode. Open Receipt shows immutable facts; Copy Receipt copies concise source-free text.

### Alerts

Lists local redacted alerts. Open follows only validated project-bound routes. Read/mute/clear behavior affects local notification state, not evidence truth. Forged, deleted, stale, or cross-project destinations fall back safely.

### Settings

Controls local preferences, notifications, close/background policy, Start at Login, monitoring policy, allowed hours, daily budgets, Quiet Mode, Battery Saver behavior, onboarding replay, diagnostics, disconnected projects, and Product Self-Test. Settings never enable cloud/source upload.

### Diagnostics

Shows app/engine/schema versions, local storage aliases, privacy/network facts, packaged capability, lifecycle state, updater/signing limits, and sanitized logs. Run Self-Test uses disposable local fixtures and must not touch a real project.

### Demo Lab

Creates a disposable local project for learning and product checks. Actions can capture Known Good, introduce a controlled regression, validate a candidate, Apply, and demonstrate rollback. Demo labels are explicit and are not real-project evidence.

## Phase 15 screen-by-screen guide

### 00 — Product lock overview

Purpose: introduce the locked-baseline rule before an operator handles behavior evolution.

Visible items: Phase heading, current product state, Baseline Lock explanation, intentional-change question, Local Only badge, existing lineage, Known Facts, and Honest Boundaries. No promotion control is offered in this overview.

Expected use: read the rule, then open the changed behavior and classify it. The current Known Good remains immutable.

![Product lock overview — top](images/00-product-lock-overview-part-01.png)

Top view: shell, product-law headline, state strip, and Baseline Lock card.

![Product lock overview — scrolled](images/00-product-lock-overview-part-02.png)

Scrolled view: existing lineage plus facts and unresolved physical/signing boundaries.

### 01 — Current Known Good locked

Purpose: confirm that a newly observed result cannot silently replace accepted proof.

Controls/items: no direct Replace action; Local Only badge; current Version 1 lineage entry with immutable identity and accepted time. The operator must use the change-decision flow.

Expected result: direct baseline acceptance is blocked while the current lineage root remains byte/record unchanged.

![Current Known Good locked — top](images/01-current-known-good-locked-part-01.png)

![Current Known Good locked — scrolled](images/01-current-known-good-locked-part-02.png)

### 02 — Change decision required

Purpose: classify an observed behavior difference without guessing.

Controls:

- Reason field: mandatory for Expected Change.
- Yes — this change is expected: records a source-bound expected-change decision; it does not promote.
- No — this is a regression: keeps the current baseline and routes the evidence into regression handling.
- I'm not sure: keeps the baseline and preserves uncertainty.

Expected result: the chosen decision is durable and project/behavior/source-bound. No source file is changed.

![Change decision — top](images/02-change-decision-required-part-01.png)

![Change decision — scrolled](images/02-change-decision-required-part-02.png)

### 03 — Expected change reverified

Purpose: require fresh evidence before promotion is even offered.

Controls/items:

- Fresh comparable verification callout: explains that the proposal passed but the baseline is unchanged.
- Verify Expected Change: runs the exact approved behavior with the current Runtime Profile and source identity.
- Lineage: continues to show only the current immutable root until promotion completes.

Expected result: PASS creates a short-lived promotion opportunity. FAIL, flaky, unavailable, non-comparable, stale, cancelled, unknown, unsupported, or timeout cannot promote.

![Expected change reverified — top](images/03-expected-change-reverified-part-01.png)

![Expected change reverified — scrolled](images/03-expected-change-reverified-part-02.png)

### 04 — Promotion confirmation

Purpose: make promotion deliberate and reviewable.

Controls/items:

- Current immutable Known Good: old proof identity.
- Proposed verified run: new comparable PASS identity.
- Explicit confirmation checkbox: required grant for this one promotion.
- Promote New Known Good: consumes the single-use short-lived token.
- Cancel: preserves the current baseline and cancels the opportunity.

Expected result: source freshness is rechecked at submission. A changed source or reused/expired token blocks promotion.

![Promotion confirmation — top](images/04-promotion-confirmation-part-01.png)

![Promotion confirmation — scrolled](images/04-promotion-confirmation-part-02.png)

### 05 — New Known Good promoted

Purpose: show completion without erasing history.

Visible items: Version 2 marked Current Known Good, operator reason, verified run, acceptance time, Version 1 retained below as immutable superseded history, Known Facts, and Honest Boundaries.

Expected result: subsequent comparable checks use Version 2; Version 1 remains readable and unchanged.

![Known Good promoted — top](images/05-known-good-promoted-part-01.png)

![Known Good promoted — scrolled](images/05-known-good-promoted-part-02.png)

### 06 — Repair verified before Apply

Purpose: explain exactly what has and has not happened before a live write.

Controls/items:

- Three verified facts: tested away from live source, protected behavior passed, live source matched.
- Transaction timeline: completed/current/pending steps, never implied by color alone.
- Review Repair: inspect selected files and technical contract.
- Apply Checked Repair: begins only after explicit confirmation in the normal repair flow.

Expected result: Safety Snapshot/journal/live verification do not appear completed early. Apply remains operator-controlled.

![Repair verified — top](images/06-repair-verified-part-01.png)

![Repair verified — scrolled](images/06-repair-verified-part-02.png)

### 07 — Live repair progress

Purpose: show real transaction progress after confirmation.

Visible items: source check, Safety Snapshot, Apply, current live recheck, pending restoration step, and explanatory contract. Buttons that would begin a second Apply are absent while work is active.

Expected result: the surface advances only from engine events. Closing/reopening the window must not invent completion or create another transaction.

![Live repair progress — top](images/07-repair-live-progress-part-01.png)

![Live repair progress — scrolled](images/07-repair-live-progress-part-02.png)

### 08 — Byte-identical rollback complete

Purpose: report a failed live post-check without falsely calling the repair successful.

Visible items: Rolled Back Safely state, restored transaction step, “Previous source restored byte-for-byte,” “Nothing else was changed,” and candidate-still-available notice.

Expected result: the message appears only after affected paths match the Safety Snapshot; unrelated paths are untouched.

![Rollback complete — top](images/08-repair-rolled-back-part-01.png)

![Rollback complete — scrolled](images/08-repair-rolled-back-part-02.png)

### 09 — Yak Receipt with passing evidence

Purpose: provide one immutable local truth record after a settled Episode.

Controls/items:

- Close: dismisses the receipt without deleting it.
- Totals: considered, checked, passed, confirmed, deferred, unknown.
- Runtime unavailable, omitted, and source-modified rows.
- Evidence rows: behavior alias, honest result, probe/run identity.
- Copy Receipt: copies concise human-readable text.
- Technical Details: exposes bounded identifiers and digest, not raw evidence/source.

Expected result: repeated creation returns the same immutable receipt/digest for the Episode.

![Yak Receipt pass — top](images/09-yak-receipt-part-01.png)

![Yak Receipt pass — scrolled](images/09-yak-receipt-part-02.png)

### 10 — Yak Receipt with unknowns

Purpose: prove that omitted and unavailable work is not painted green.

Visible items: lower checked/passed totals, deferred/unknown totals, separate Runtime Unavailable and Omitted counts, one actual PASS row, source-modified No, and honest boundary explanation.

Expected result: unknown stays unknown; deferred is not counted as checked; no confidence percentage is shown.

![Yak Receipt unknowns — top](images/10-yak-receipt-unknowns-part-01.png)

![Yak Receipt unknowns — scrolled](images/10-yak-receipt-unknowns-part-02.png)

### 11 — Intel Mac package status

Purpose: separate local technical readiness from trusted public distribution.

Visible items: version, x86_64 architecture, database schema, automated test count, installed-app/DMG/lifecycle facts, and public-release blocker.

Expected result: ad-hoc/local success never appears as Developer ID/notarized/public-ready. The operator must resolve signing and physical acceptance separately.

![Intel Mac package status — top](images/11-intel-mac-package-status-part-01.png)

![Intel Mac package status — scrolled](images/11-intel-mac-package-status-part-02.png)

## Operator workflows

### Accept an intentional behavior change safely

1. Open Project → Behaviors and select the changed protected behavior.
2. Compare the current evidence to the current Known Good.
3. Choose Yes — this change is expected and enter a specific reason.
4. Select Verify Expected Change.
5. Wait for a fresh comparable PASS on the exact current source/runtime.
6. Review old versus proposed Known Good.
7. Check the explicit confirmation and select Promote New Known Good.
8. Confirm that the new version is Current and the old version remains in lineage.
9. If source changes at any point, stop and reverify; never work around the stale block.

### Handle a real regression

1. Choose No — this is a regression or open the confirmed Regression Detail.
2. Review prior PASS, current repeated comparable failure, retries, and impact boundary.
3. Create a Repair Workspace only when eligible.
4. Review/edit the candidate in isolation.
5. Validate the candidate and confirm the protected behavior passes away from live source.
6. Review Repair and inspect selected-file scope.
7. Explicitly confirm Apply.
8. Watch the live transaction states.
9. On success, require fresh live PASS before “Protected again.”
10. On failure, wait for byte-identical restoration; do not call the repair done.

### Create and use a Yak Receipt

1. Open Project → Memory or the settled Episode.
2. Select Create Yak Receipt.
3. Review considered/checked/passed/confirmed/deferred/unknown totals.
4. Inspect Runtime Unavailable and Omitted separately.
5. Verify Source Modified by Yak matches the actual Episode outcome.
6. Select Copy Receipt for concise text or Technical Details for bounded identifiers.
7. Treat missing/unknown evidence as an explicit limitation.

### Install the Intel technical preview

1. Verify the DMG filename/version and SHA-256 from the master report.
2. Mount the DMG and inspect the application identity.
3. Preserve the prior installed app recoverably.
4. Copy MellowYak to Applications.
5. Launch only in a controlled local environment; this build is ad-hoc signed and not notarized.
6. Confirm version 0.5.0-preview.1, one desktop process, and one engine.
7. Explicitly Quit and confirm both processes exit.
8. Do not distribute publicly or instruct users to bypass Gatekeeper.

## What the operator should expect next

The current installed Intel app is operational under automated validation, but final product lock remains blocked until a human completes the physical matrix documented in the master report. The next acceptance session must use the exact installed hashes, capture timestamped native evidence without unrelated/private windows, perform one physical action at a time, record PASS/FAIL/BLOCKED honestly, and rebuild/retest only if a defect requires code change.

Windows, Linux, Apple Silicon, Developer ID enrollment, notarization, public release, production updater publication, cloud/account work, and new product features are outside Phase 15M.
