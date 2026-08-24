# Phase 7 research-source summary

The complete source record, versions, access date, and exact decisions are in
[`../research/PHASE_7_TECHNICAL_SOURCES.md`](../research/PHASE_7_TECHNICAL_SOURCES.md).

Research was bounded to official primary documentation and did not upload repository source,
evidence, paths, or project data.

## Decisions informed

- Python `os.replace`, `fsync`, `hashlib`, JSON, and `pathlib` documentation informed atomic
  publication, SHA-256 identity, canonical manifests, and path confinement.
- Python `subprocess`/`shutil.which`, Python environment and PyPA specifications informed executable
  discovery, argv-only execution, and metadata-only environment handling.
- Node.js CLI/child-process and npm script documentation informed version discovery and the rule that
  package scripts require explicit approval and are never run during detection.
- PHP CLI/manual and Composer schema documentation informed bounded version/SAPI/extension metadata
  and manifest hashing without `phpinfo()` or stored configuration values.
- Node filesystem-watch caveats informed settle-window Episodes plus authoritative filtered rescan and
  polling/reconciliation fallback.
- Tauri 2 command, capability, sidecar, tray, and distribution documentation informed keeping heavy
  work in the authenticated engine and preserving least-privilege packaged sidecar lifecycle.

## Dependency decision

The implementation uses the repository's existing standard-library, FastAPI, SQLAlchemy/Alembic,
watching/ignore, Tauri, and browser stack. Phase 7 selected no new runtime dependency and therefore
adds no new dependency license.
