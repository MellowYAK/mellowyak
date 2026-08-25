# Phase 11M implementation report

## Implemented

- Removed the First Run controlled/uncontrolled React transition and added a console regression test.
- Split the frontend into measured React, translation, Tauri, Product Truth and acceptance chunks;
  the >500 kB advisory is gone.
- Replaced the macOS PyInstaller onefile sidecar with a packaged onedir engine resource, reducing
  warm/restart handshake time substantially while preserving the offline package.
- Added supervised macOS engine restart, resource-selection and handshake events, single-instance
  lifecycle acceptance and explicit child cleanup.
- Added native notification action waiting so navigation happens only on activation.
- Added a disposable polyglot macOS Acceptance Lab with a permanent synthetic marker.
- Added case-sensitive APFS filesystem safety, two-version updater, signing readiness, lifecycle,
  package and performance validators.
- Added Intel and same-source arm64 macOS CI build paths without automatic publishing.
- Rebuilt the Intel `.app` and DMG, applied an ad-hoc structural signature, and inspected the DMG
  read-only.

## Architecture

Phase 10 already used ADR numbers 0037 and 0038, so Phase 11M deliberately uses the next unique
numbers 0039–0042 rather than overwriting accepted history. No database field was justified and no
migration was added.

## APC boundary

No APC code, runtime, credential, data, project or deployment was read or modified. This phase uses
only MellowYak's existing independently implemented services and synthetic fixtures.
