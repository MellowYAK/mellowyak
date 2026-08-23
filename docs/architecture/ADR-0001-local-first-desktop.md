# ADR-0001: Local-first desktop architecture

- Status: Accepted
- Date: 2026-08-23

## Decision

MellowYak is one installable Tauri 2 desktop application. React, TypeScript and Vite provide the UI; a Python 3.12-compatible FastAPI/Pydantic/SQLAlchemy engine is bundled as a PyInstaller sidecar; Alembic manages a local SQLite database. Large evidence stays in platform-native filesystem folders, with SQLite reserved for metadata.

## Rationale

A desktop app keeps private project data at its source, works without an account or server, and supports passive local observation later. Tauri provides a small native shell and explicit capability model without bundling a Chromium/Node runtime as Electron does. Streamlit is a development web surface, not a secure native packaging/process boundary. Python remains appropriate for future analysis and browser ecosystems and is invisible inside the bundle. SQLite removes MariaDB administration while retaining transactions and migrations.

APC's Bridge contained useful transport/execution lessons but existed because APC was a server product. In MellowYak that boundary becomes the supervised Local Engine. A connector is an opt-in path to an external model/tool; an execution arm performs a bounded action. Keeping them separate prevents connector permission from silently becoming machine-control permission.

An optional team server may later synchronize explicitly selected metadata through a separate adapter. It will not replace the local engine or become mandatory. The end-user contract remains one application: shell, frontend, engine, SQLite library and runtimes are packaged together.

## Consequences

Native packages must be built and tested per operating system. Signing, notarization and production installer hardening remain release work. Phase 1 contains no project scanner, connector, browser runtime or regression engine.
