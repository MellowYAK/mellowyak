# Save Points, Episodes, and Known-Good milestones

MellowYak keeps incremental local source memory without requiring Git. The product separates three
ideas that must not be confused:

- **Episode** — a settled burst of related file events;
- **Save Point** — an exact local source snapshot;
- **Known-Good milestone** — a pinned Save Point with passing probe evidence or explicit human
  attestation.

A Save Point alone says what source MellowYak stored. It does not prove that any behavior worked.

## How Episodes are created

Rapid editor, formatter, dependency, or tool writes are coalesced. After the paths settle—or after a
bounded maximum duration—one stable Episode creates at most one normal snapshot. If the resulting
manifest is identical to the previous one, the Episode remains in history and the previous snapshot
is reused.

Watcher failure does not block source writes. MellowYak can report the failure and use bounded
reconciliation/polling while the editor continues normally.

## How incremental storage works

Each eligible file is hashed with SHA-256. Unchanged content points to an existing local object rather
than being copied again. The **Memory / Save Points** screen distinguishes:

- logical bytes represented by a snapshot;
- new physical bytes added;
- bytes reused through deduplication;
- included, excluded, sensitive, and unsupported file counts;
- optional Git anchor;
- manifest/source identity and integrity status.

Snapshot objects and manifests live under the MellowYak application-data root, not in the project.
SQLite stores metadata and references, not source blobs.

## Default exclusions

Capture respects project ignore rules and excludes sensitive/provider-private content, MellowYak-owned
data, escaping symlinks, generated/artifact directories, and files above configured object limits.
Unsupported and excluded counts remain visible. A Save Point cannot reproduce a file that was
intentionally excluded.

## Memory screen actions

Open a project and select **Memory** to:

- create a manual Save Point;
- review the Episode timeline;
- select and inspect Save Point metrics;
- load the bounded entry manifest;
- pin or unpin an unreferenced Save Point;
- materialize an isolated verified copy outside the live project;
- create a Known-Good milestone;
- inspect configured retention days and storage soft cap.

Materialization never writes to the selected source folder. It creates a new MellowYak-owned folder
and verifies object digests before writing.

## “This works — save it”

Use this action only after the current state genuinely works.

1. Let the current Episode settle.
2. Create or reuse the current Save Point.
3. Select the relevant behavior and probe when automation exists.
4. Run the probe and require PASS; otherwise make an explicit human attestation.
5. Name the milestone and save it.

The milestone pins the exact snapshot and records the behavior/probe/runtime versions, evidence,
environment summary, limitations, and whether confirmation was manual. A raw snapshot is never
promoted silently.

## Retention

The Beta default is 30 days and a 5 GiB soft cap per project. Projects can configure both values.
Reference-safe cleanup protects current history and anything referenced by a pinned milestone,
baseline, incident, or Repair Workspace. A soft cap is a cleanup target, not an immediate destructive
quota.

## Git and non-Git projects

Git projects may show branch, HEAD, and worktree information in technical details. Non-Git projects
receive the same source scan, Episode, Save Point, milestone, probe, signal, and Repair Workspace
workflow using snapshot lineage. Git is useful evidence, not a requirement.

## What Save Points are not

Save Points are not a cloud backup, Git replacement, process-memory checkpoint, deployment rollback,
or proof that every behavior works. Keep your normal source control and backup practices.
