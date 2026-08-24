# Releases and in-app updates

Phase 4 packages stage a platform-matching Playwright Chromium tree before the Tauri build. A release artifact is not valid unless the installed sidecar reaches migration `0004_behavior_evidence_browser`, the packaged executable completes the local PulsePlan reschedule capture, start/final evidence hashes verify after restart, and shutdown leaves no engine/browser process. Browser assets increase package size and must be recorded before/after. No Phase 4 release is published by the implementation task; the signed updater remains implemented but not end-to-end runtime verified until a higher signed GitHub Release exists.

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
