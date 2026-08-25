# Activity and regression guide

## Activity and Episodes

Activity is chronological and project-scoped. Each row represents an Episode or exact operational
event, with a bounded summary, source identity, check counts, limitations and final signal. Pagination
prevents an unbounded history query. Episode Detail correlates Save Points, milestones, impact,
verification, regression and recovery facts without inventing missing relationships.

## Regression Detail

A confirmed regression requires comparable accepted prior PASS evidence and reproducible current
FAIL evidence, or the independently supported regression engine. The friendly view explains what is
known, what was expected, what failed and what to do next. Technical disclosure contains exact reason
codes, evidence identifiers, affected paths and provenance. Root cause remains unknown unless evidence
actually proves it.

## Repair path

The Repair Workspace is an isolated copy. A candidate is a bounded manifest of exact changes, not a
repair claim. Workspace validation must pass the original failed Probe and every required check for the
exact candidate identity. `Validated` does not mean `Applied`. Live Apply requires a fresh source
preflight, explicit confirmation, Safety Snapshot, journal, writes and fresh live verification.

Rollback is transaction-scoped. It restores affected paths and verifies byte identity; it does not
blindly restore arbitrary history or discard unrelated work.
