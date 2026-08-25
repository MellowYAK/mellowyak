# Diagnostics and Product Self-Test guide

## Diagnostics

Diagnostics shows actual local engine, authentication boundary, database/schema, storage integrity,
browser/runtime availability, package/platform state, activity mode and bounded recent events. It
uses redacted aliases instead of bearer tokens, private source content or full user paths.

Use **Refresh** after a local change. Use **Copy diagnostics** only for the bounded redacted summary.
Create a support bundle only when needed, review its included/excluded manifest and integrity hash,
then decide manually whether to share it. There is no automatic support upload.

## Product Self-Test

Product Self-Test creates a disposable synthetic project and executes named steps for database,
snapshot, known-good evidence, regression, Repair Workspace, invalid/valid candidates, Safety
Snapshot, Apply, post-check, rollback, crash journal, no-network, no-orphan and cleanup behavior.
The result table distinguishes PASS, FAIL and steps that did not execute. It must never display success
for a skipped or unimplemented step.

Self-Test does not validate a user's private project, platform signing, native notification clicks,
production updater delivery or every supported operating system. It is a local product-health aid,
not certification.
