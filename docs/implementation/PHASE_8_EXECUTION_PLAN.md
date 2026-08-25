# Phase 8 execution plan

Date: 2026-08-25

Phase 8 extends the Phase 7 Repair Workspace rather than creating a second repair system.

1. Add migration `0008_validated_repair_apply` for candidate revisions, immutable validation
   records, Apply transactions/files/journal events, rollback/recovery records, Demo Lab runs, and
   Product Self-Test runs.
2. Fingerprint the isolated workspace against its immutable base snapshot and build deterministic
   bounded ADD/MODIFY/DELETE/RENAME candidate manifests without storing source content in SQLite.
3. Validate the exact candidate digest inside the workspace. The original failed Probe is first;
   required impacted checks block validation and suggested checks remain advisory.
4. Separate ANALYZE, VALIDATE, PREPARE, COMMIT, and ROLLBACK capabilities. COMMIT requires a
   short-lived, one-time, project/candidate/source-bound confirmation nonce.
5. Before any live write, settle source state, create and pin a fresh Safety Snapshot, re-hash every
   affected path, and create a durable operation journal.
6. Apply bounded same-filesystem temporary-file replacements, safe renames, and deletions last.
   Fresh live verification is mandatory; workspace evidence is never reused as live evidence.
7. On any Apply or post-verification failure, restore only transaction paths from the Safety
   Snapshot and prove byte equality. Unprovable recovery stops writes and creates a redacted bundle.
8. Add a synthetic offline Demo Lab and disposable Product Self-Test covering valid Apply, stale
   blocking, rollback, and crash recovery without touching real projects.
9. Add authenticated typed APIs/events and professional React screens using translation keys only,
   with full English/Hebrew RTL parity and reduced-motion support.
10. Preserve all prior tests, add Phase 8 security/transaction tests, rebuild the Intel macOS app and
    DMG, run packaged flows, and place reports/screenshots only in `docs/phase-8-delivery/`.

Exclusions: no AI/model calls, coding-agent connector, automatic repair generation, automatic Apply,
three-way merge, arbitrary historical in-place restore, cloud upload, deployment, signing, release,
or APC modification.
