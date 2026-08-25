# Phase 8 implementation report

## Result

Phase 8 extends the existing MellowYak architecture from an isolated Repair Workspace to a bounded,
validated, explicitly confirmed Apply transaction. It never generates a repair with AI, never reads
coding-agent conversations, never uploads source/evidence, and never copies an old project tree over
the live source.

## Implemented lifecycle

1. The existing confirmed-regression record creates an isolated workspace from an exact snapshot.
2. A deterministic manifest comparison produces a revisioned Candidate Patch with ADD, MODIFY,
   DELETE, safe identical-content RENAME, and supported mode metadata.
3. Candidate validation binds exact candidate, workspace, source, runtime-profile, and policy
   identities. The original failed Probe is first and required impacted/runtime checks block Apply.
4. `PREPARE_APPLY` rechecks the current project, affected paths, candidate state, and active
   transaction exclusion without granting write permission.
5. A short-lived, one-time, project/candidate/source-bound confirmation capability is returned only
   for a validated current candidate.
6. Deliberate confirmation creates a fresh pinned pre-Apply safety snapshot and durable ordered
   journal before the first live write.
7. Bounded same-filesystem temporary files, atomic replacements where supported, late deletions,
   path re-hashing, mode preservation, and journal events implement the transaction.
8. A new live source identity and fresh live verification run separately from workspace evidence.
9. Success commits the transaction without automatically replacing Known Good. Failure restores only
   transaction paths from the exact safety snapshot and proves byte identity.
10. Startup recovery inspects incomplete journals. Unprovable recovery stops writes, raises a critical
    local state, and creates a redacted Recovery Bundle.

## Storage and API

Migration `0008_validated_repair_apply` adds candidate, candidate-file, candidate-validation,
validation-item, Apply transaction, transaction-file, journal-event, rollback, recovery-bundle,
Demo Lab, and Product Self-Test records. Completed validation and transaction evidence is treated as
immutable. Candidate bytes remain in the workspace/content-addressed store, not SQLite.

The authenticated loopback API exposes typed candidate, validation, Apply, recovery, portable export,
Demo Lab, and self-test endpoints. OpenAPI remains deterministic and generates the TypeScript client.

## Safety limits

- 250 candidate files; 64 MiB logical candidate bytes; 10 MiB per file.
- 1 MiB preview; bounded diff lines and bounded process output.
- Symlinks, hard links, device/special files, traversal, escape, sensitive paths, and case collisions
  are blocked.
- Binary Apply is blocked by default unless a separate advanced confirmation policy enables it.
- One active Apply per project; validation concurrency two; bounded timeouts.
- No shell, no arbitrary commands, no Git reset/checkout/clean, no automatic merge.

## Demo and self-test

The opt-in Demo Lab creates a small offline synthetic checkout service in a user-selected directory.
It supports deterministic known-good, confirmed regression, bad candidate, valid candidate, stale
source, Apply, post-Apply failure, rollback, recovery, non-Git, and reset scenarios. Its marker and
database identity prevent Demo actions from targeting a real project.

Product Self-Test uses disposable temporary storage only. It exercises migration, snapshot and CAS
deduplication, runtime identity, known-good Probe, confirmed regression, workspace, candidate
rejection/validation, safety snapshot, Apply, post-verification, rollback, crash journal, hashes,
network prohibition, cleanup, and orphan-process absence, and produces PASS/PARTIAL/FAILED evidence.

## UI and language

Regression Detail contains the real Repair Workspace workflow. Demo Lab and Product Self-Test are
available as explicit product surfaces. Twenty-six deterministic delivery states cover success,
blocked, failure, rollback, recovery, demo, self-test, and Hebrew RTL. All visible UI copy uses the
English-base/Hebrew translation catalogs; no hardcoded visible copy was introduced.

## APC provenance

APC was not modified. No APC PHP, MariaDB, Bridge, queue, tenant, credentials, backup/restore, coding-
agent connector, or UI code was copied. Snapshot, evidence, and selective-restore ideas were treated
only as historical product lessons; Phase 8 is a clean extension of MellowYak's local architecture.

## Honest limitations

Phase 8 does not provide automatic repair creation, automatic Apply, a three-way merge, general
historical restore, cross-filesystem atomic transactions, external database isolation, production
deployment verification, cloud backup, or coding-agent integration. Windows, Linux, Apple Silicon,
signing, notarization, and public updater delivery require later platform-specific runtime evidence.
