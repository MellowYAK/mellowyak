# APC extraction note — Phase 7

## Read-only boundary

APC was not modified. MellowYak remains a separate public repository with its own local Python
engine, SQLite/Alembic schema, React/Tauri desktop, tests, packages, and documentation. No APC server,
database, deployment, user account, credential, private host, or runtime data is part of Phase 7.

## Product lessons retained

Earlier read-only APC review documented useful product concepts around project history, source state,
evidence, local runtime status, and focused repair context. Phase 7 uses those lessons only as product
requirements:

- several runtimes may belong to one project;
- meaningful change history needs grouping rather than raw event noise;
- evidence must stay bound to exact source/runtime state;
- repair work should occur in an isolated copy, never by overwriting the live project.

## Clean MellowYak implementation

- Runtime Profiles and adapters are new typed Python services and `0007` records.
- Snapshot memory is a new local SHA-256 object/manifest store outside the live project.
- Episodes extend the existing MellowYak watcher/Change architecture.
- Universal Probes extend the existing MellowYak Browser Replay, Protection Plan, regression, and
  Completion Gate architecture.
- Repair Workspace v1 materializes MellowYak snapshots under the MellowYak data root.
- Runtime Wizard, Runtime, Memory, Probe, signal, and workspace UI use MellowYak React components and
  English/Hebrew translation catalogs.

## Permanently excluded APC surfaces

APC PHP, MariaDB, tenancy/roles, Docker/server topology, broad source/model readers, installation-wide
authorization, Bridge/agent connectors, task queues, credentials, remote control, and deployment code
remain `DO_NOT_USE`, `ARCHIVE`, or `SECURITY_BLOCKER` as recorded in the migration matrix.

## Continuation rule

Future MellowYak work continues from the Phase 7 branch/commit in this repository. It must not edit
APC to deliver MellowYak capabilities and must preserve the translation-only GUI, local-data
separation, prompt-blind design, and source-safe Repair Workspace boundary.
