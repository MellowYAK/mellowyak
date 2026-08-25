# Releases and in-app updates

## Phase 9 Technical Preview package gate

A Phase 9 package must be fresh from the exact candidate commit, report version
`0.2.0-preview.1`, embed migration `0009_technical_preview_readiness`, preserve Phase 8 records and
installation identity, and pass both packaged Phase 8 safety and Phase 9 readiness against the final
sidecar. The gate uses isolated synthetic data and proves first-run persistence/replay, disconnected
history, identity-safe reconnect/relocate, private tray/routes/diagnostics, support redaction, storage
integrity, activity-mode safety, clean install, Phase 8 upgrade, single-instance, close-to-tray,
explicit Quit, and zero orphans.

The disposable local updater fixture must accept the correct signature and reject tamper, wrong key,
lower/no-update replacement, and interrupted content without persisting its private key or changing
production updater configuration. This fixture is not a public update service. A production updater
claim still requires a higher, platform-signed, updater-signed immutable release and installed
cross-version evidence.

The current Intel macOS app/DMG may be used only as unsigned local operator evidence. Apple Silicon,
Windows, and Linux matrices are workflow configuration until their native artifacts are built,
installed, exercised, and inventoried. Public distribution remains blocked on platform signing,
notarization where applicable, updater delivery, provenance, and real-project disposable-copy
operator acceptance.

## Phase 8 package gate

A Phase 8 package must be built fresh from the exact Phase 8 local commit. It must embed migration
`0008_validated_repair_apply` and must not reuse a Phase 7 application, DMG, sidecar, engine, or
browser tree as evidence. Generated `.app`, DMG, PyInstaller, Rust target, runtime database,
Repair Workspace, journal, recovery, and Demo Lab output remains outside Git history.

The packaged gate uses disposable synthetic source only and must prove: candidate generation;
workspace-only validation; a candidate/project/source-bound deliberate Apply confirmation; a fresh
pinned safety snapshot; hash-preconditioned journaled writes; separate fresh live verification;
byte-identical rollback after a simulated post-Apply failure; incomplete-journal detection; and the
local Product Self-Test. No package may claim AI repair, automatic Apply, general historical restore,
cloud backup, or production deployment safety.

Windows and Linux workflows compile the same Phase 8 schema and contracts, but configured CI is not
runtime verification. Intel macOS is the only platform covered by this phase's local packaging gate;
Windows, Linux, Apple Silicon, code signing, notarization, and public updater delivery remain
unverified until platform-specific evidence exists.

## Phase 7 package gate

A Phase 7 package must be built fresh from the exact final commit. Do not reuse a Phase 6 `.app`,
DMG, sidecar, browser tree, size, or hash. The embedded engine must migrate through
`0007_runtime_snapshot_probe_foundation` and pass packaged-engine smoke plus
`scripts/validate_packaged_phase7.py`.

The packaged Phase 7 validator must prove, using disposable public fixtures:

- a non-Git project can scan, snapshot, create a milestone, run a Probe, restart, and reload;
- unchanged snapshot objects are reused and logical/new/reused byte counts are recorded;
- an accepted comparable Probe PASS followed by current FAIL and retry FAIL can produce
  `CONFIRMED`, while file-change-only and flaky scenarios do not;
- a Repair Workspace materializes outside live source, contains no secret fixture values, and leaves
  the live project unchanged;
- runtime/probe children are cancelled/cleaned and local API auth/loopback checks remain intact.

Record fresh `.app`/DMG sizes, desktop/engine/Chromium/DMG SHA-256 values, startup time, snapshot
throughput and storage metrics, and Probe runtime in the Phase 7 validation report. Inspect the DMG by
checksum, read-only mount, application/Applications-link presence, and clean unmount. Generated
packages remain outside Git history.

Windows and Linux workflows must install/build the same locked dependencies and migration, but a
configured workflow is not runtime verification. Do not claim Windows, Linux, Apple Silicon, PHP
execution, signing, notarization, updater delivery, or a public release without exact evidence.

Phase 5 packages stage a platform-matching Playwright Chromium tree before the Tauri build. A release artifact is not valid unless the installed sidecar reaches migration `0005_verification_regression_gate` and `scripts/validate_packaged_phase5.py` completes the packaged PulsePlan baseline, seeded assertion failure, supported regression, blocked gate, Repair Context, repaired source identity, re-verification, VERIFIED_COMPLETE, restart/history reload, loopback authentication, and orphan-process checks. Browser assets and all artifact hashes/sizes must be recorded. No Phase 5 release is published by the implementation task; the signed updater remains implemented but not end-to-end runtime verified until a higher signed GitHub Release exists.

MellowYak source is public, but installers are distributed only through GitHub Releases. A version tag builds the exact tagged commit on macOS, Windows, and Linux and publishes the platform installer plus Tauri's signed update metadata.

## User path

- macOS: install the DMG once by dragging `MellowYak.app` to Applications. Later signed versions are offered inside the installed app.
- Windows: install the NSIS `.exe` once. Later signed versions use the updater's passive installer mode.
- Linux: the AppImage supports signed in-app replacement. A `.deb` is also published for installation, but package-managed `.deb` upgrades remain a package-manager/manual operation.
- The updater checks the public `latest.json` on GitHub Releases. It never downloads source code or a separate MellowYak engine: each platform update already contains the matching local engine sidecar.

## Local macOS development

Do not build or drag a DMG after each local change. Run:

```bash
python3 scripts/dev.py install-macos
```

This builds only the app bundle, closes the running local copy, installs `/Applications/MellowYak.app`, retains the prior bundle under a timestamped `/Applications/MellowYak-previous-*.app` path for recovery, and launches the new copy.

## Signing boundary

Tauri update verification cannot be disabled. The committed application contains only the public updater key. The private key is intentionally outside the repository and must be backed up securely. Configure these GitHub repository secrets before creating a version tag:

- `TAURI_SIGNING_PRIVATE_KEY`: contents of the private updater key;
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: empty for the current passwordless automation key, or the password if the key is rotated before the first public release;
- platform code-signing and notarization credentials before calling macOS or Windows artifacts production-ready.

Keep the local private key under `~/.tauri/mellowyak-updater.key` with owner-only permissions. Never commit or print its expanded absolute path. Its public-key SHA-256 is `c3c6380738e251e833bcaaca316d9f7a12a1c7a2024329528cdc62662c223cc3`.

## Publishing guard

Before pushing a tag, update the single application version in `apps/desktop/src-tauri/tauri.conf.json`, verify the tag matches it, run the full local quality suite, and confirm the signing/notarization secrets. The release workflow verifies tests and translation-key policy before building. No workflow or source build may print the private signing key.
