# MellowYak Phase 7 implementation report

Date: 2026-08-24

Starting branch: `product/desktop-productization-tray-notifications`

Starting commit: `7a02e9d4d01ff68c472f21fa1d1ccca929327fc4`

Safety tag: `phase-6-desktop-productization-handoff-2026-08-24`

Implementation branch: `product/runtime-snapshot-probe-foundation`

Migration: `0007_runtime_snapshot_probe_foundation`

## Outcome

Phase 7 extends the existing authenticated local engine with versioned Runtime Profiles, optional-Git
source identity, Episode grouping, a local content-addressed snapshot store, Save Points, known-good
milestones, universal Probes, deterministic signal states, and isolated Repair Workspaces. The
desktop adds an eight-step Runtime Wizard plus Runtime and Memory surfaces in English and Hebrew RTL.

This is an implementation description, not a validation verdict. Exact final test, package, timing,
deduplication, and platform results remain in `VERIFICATION_EVIDENCE.md` and must not be inferred from
the presence of code.

## Runtime setup

The Runtime Wizard collects project type, detected runtime candidates, explicit primary/secondary
selection, executable/argv, project-relative working directory, ports, loopback health, approved
tests, observation level, retention, and storage cap before creating an initial Save Point. Existing
projects without profiles continue source monitoring and can complete setup later.

`runtime_profiles` hold stable identity and current status. Immutable `runtime_profile_versions`
preserve the exact approved execution definition. Detection, validation, instances, and sanitized
runtime events are separate records. Python, Node, PHP, generic process, and metadata-only
Ruby/Java support share one adapter contract and fail open when unavailable.

## Source memory

Git remains an optional anchor. Source Identity v2 can bind a state through snapshot parent/current
IDs, manifest digest, and Episode ID. Existing Git-derived Change records stay valid.

The snapshot store lives below the MellowYak data root and outside source. Canonical SHA-256 manifests
reference atomic content-addressed objects; SQLite stores metadata/references only. Capture enforces
ignore, sensitive/provider-private, size, data-root, and symlink boundaries. Unchanged object digests
are reused. Integrity is checked before detail display or materialization.

The Episode service coalesces bounded filesystem hints and creates at most one snapshot after a
settle window. Identical manifests reuse the prior snapshot. Failures report state but never block
the editor or source writes.

## Save Points and known good

Memory displays Episodes, Save Points, physical bytes added, reused bytes, retention, pins, and
technical identity. A user can materialize a verified snapshot to a new MellowYak-owned local folder
without touching live source.

“This works — save it” creates a pinned milestone only when a configured automatic Probe passes or
the user explicitly attests. A snapshot alone is not a behavior baseline and does not silently create
a Protected Behavior.

## Universal Probes and signals

Versioned Browser, API, CLI, Process, Test, and Manual Probes bind runs to exact source and optional
runtime identities. Browser delegates to the existing replay path. API remains loopback-first. CLI
and test execution use executable plus argv with no shell, bounded output/time, cancellation, and
cleanup. Manual evidence remains explicitly manual.

Selection extends the existing Impact graph and Protection Plan with bounded provenance-aware probe
selection. It reports truncation/unknowns and does not claim that every dependent page was checked.

Signals supplement the existing Completion Gate:

- source/impact change only: `WATCH`;
- one unconfirmed failure/anomaly: `SUSPECTED`;
- related crash or accepted PASS followed by one FAIL: `HIGH`;
- comparable accepted PASS followed by reproducible FAIL, or an existing supported regression:
  `CONFIRMED`.

The friendly UI explains the result and provides expandable exact technical evidence. No numeric
confidence or unproven root-cause claim is used.

## Repair Workspace v1

For a confirmed incident, MellowYak can create an isolated workspace below its data root containing a
verified materialization, bounded incident/manifest/validation JSON, and repair instructions. It is
openable and deletable locally. Phase 7 does not run an agent, generate/apply a patch, copy changes
back, modify the live project, deploy, or roll back.

## Local API and events

Typed authenticated project routes cover runtime detection/profiles/instances, snapshots,
materialization and pins, Episodes and probe selection, milestones, Probes/runs/cancellation, and
Repair Workspace lifecycle. Existing browser/evidence/behavior/verification/regression/gate APIs are
retained. New runtime, Episode, snapshot, milestone, probe, signal, and workspace events remain local.

## Database

Migration `0007_runtime_snapshot_probe_foundation` adds project runtime/memory settings and the
runtime, Episode, snapshot/object/entry/milestone, Probe/run, runtime-event, signal, and Repair
Workspace entities. It follows `0006_desktop_productization`; migrations `0001`–`0006` and their data
remain part of the required upgrade matrix.

## Privacy and security

- Local API remains bearer-authenticated and loopback-bound.
- Runtime/probe commands never invoke a shell and use confined working directories.
- Full environments, secret values, authorization/cookie fields, provider credentials, prompt
  histories, and provider-private directories are not collection targets.
- Snapshot objects, materializations, and Repair Workspaces remain under the local data root.
- No cloud snapshot/evidence/source upload, analytics SDK, account system, or coding-agent integration
  is added.
- All visible React copy uses translation keys; English is the base catalog and Hebrew is complete
  RTL.

## APC provenance

APC remained read-only. Phase 7 uses MellowYak's own Python/SQLite/Tauri architecture and carries
forward only previously documented product lessons about local project history, evidence, and safe
isolation. No APC PHP, MariaDB, tenancy, Bridge, credential, remote-control, or server-deployment code
was copied or modified.

## Explicit limitations

- Save Points are local source memory, not backup, cloud sync, process-memory checkpoints, or Git.
- Impact and probe selection remain bounded and incomplete where relationships are unknown.
- `CONFIRMED` is limited to comparable evidence; it is not a root-cause or zero-regression guarantee.
- Repair Workspace is manual isolated materialization, not repair or apply.
- Runtime availability varies by the executables present on the machine.
- Windows, Linux, Apple Silicon, signing, notarization, and remote CI were not runtime verified.
  Python, Node, and PHP approved-argv probes were verified only on the recorded local Intel macOS
  development environment; that does not establish other-platform support.
- Exact test, package, performance, and 23-screen capture results are recorded separately in
  `VERIFICATION_EVIDENCE.md`.

## Phase 8 boundary

Phase 8 may add hardened isolated candidate repair, validation, hash-preconditioned apply, a safety
snapshot, post-apply verification, and rollback. Phase 7 stops before all of those capabilities.
