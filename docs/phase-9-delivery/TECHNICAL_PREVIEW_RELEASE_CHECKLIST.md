# Technical Preview release checklist

## Source and data

- [x] Phase 1–8 compatibility tests remain green.
- [x] Phase 9 Python/React/TypeScript/Rust/Vite checks pass.
- [x] English base and Hebrew translation catalogs have parity; Hebrew is RTL.
- [x] GUI translation-key-only checker passes.
- [x] OpenAPI generation is deterministic.
- [x] Empty and 0001–0008 database migrations reach 0009 with data preserved.
- [x] No real project, APC data, user database, credentials, or external network was
  used by the automated gate.

## Current Intel macOS package

- [x] Fresh `.app` and DMG built for `0.2.0-preview.1`.
- [x] Phase 8 packaged safety gate is `VERIFIED_WORKING`.
- [x] Phase 9 packaged acceptance gate is `VERIFIED_WORKING`.
- [x] DMG checksum, read-only mount, contents, hashes, link, and clean detach pass.
- [x] Installed bundle hashes match the final package.
- [x] Clean isolated launch reaches schema 0009 and quits without orphan processes.
- [x] First run, disconnected/reconnect/relocate, tray, route validation, diagnostics,
  support redaction, updater fixtures, and Battery Saver safety pass.
- [x] Screenshots, PDF, package inventory, platform matrix, security review, updater
  report, and real-project operator guide are present.

## Public-distribution blockers

- [ ] Developer ID signing completed and recursively verified.
- [ ] Apple notarization accepted and stapled.
- [ ] Gatekeeper accepts a clean downloaded artifact.
- [ ] Production updater validated end-to-end with a higher signed release.
- [ ] Apple Silicon macOS package built and runtime accepted.
- [ ] Windows x64 installer built, signed, installed, updated, and runtime accepted.
- [ ] Linux x64 artifacts built, installed, updated, and runtime accepted.
- [ ] Human operator completes the disposable-copy real-project acceptance guide.
- [ ] Release workflow runs against the immutable final tag and emits provenance.

## Decision

**Local Intel macOS Technical Preview candidate: READY FOR OPERATOR REVIEW.**
**Public/multi-platform production release: BLOCKED.**

Do not push a version tag, publish artifacts, call the package signed/notarized, or
claim other-platform support until every applicable blocker has exact evidence.
