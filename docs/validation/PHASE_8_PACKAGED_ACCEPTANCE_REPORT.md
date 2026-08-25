# Phase 8 Packaged Acceptance Report

Date: 2026-08-25

Platform: Intel macOS (`x86_64`)

Starting branch: `product/validated-repair-safe-apply`

Starting commit: `2e6fa395c8969b14272928d3622be8185f2fe87f`

Database migration: `0008_validated_repair_apply`

## Result

The mandatory current-platform Phase 8 gate is `VERIFIED_WORKING`. The validator used the
`mellowyak-engine` executable embedded in a freshly built `MellowYak.app`, a unique temporary
application-data root, and nine synthetic Demo Labs. It did not connect a real project.

| Gate | Status | Evidence |
| --- | --- | --- |
| Packaged authenticated loopback startup | VERIFIED_WORKING | Fresh sidecar handshake, unauthenticated request rejected, schema `0008` |
| Invalid candidate | VERIFIED_WORKING | Validation became `VALIDATION_FAILED`; no live write |
| Stale source | VERIFIED_WORKING | HTTP 409 and byte-identical externally changed fixture |
| Validated Apply | VERIFIED_WORKING | Transaction `COMMITTED` after fresh live verification |
| Post-Apply rollback | VERIFIED_WORKING | Transaction `ROLLED_BACK`; affected bytes restored |
| Crash recovery | VERIFIED_WORKING | Four real process exits and restart recovery, described below |
| Recovery Required | VERIFIED_WORKING | Writes stopped, CRITICAL alert created, redacted bundle created |
| Product Self-Test | VERIFIED_WORKING | 22 executed steps reported PASS from packaged sidecar |
| Restart persistence | VERIFIED_WORKING | Self-Test history and transaction history reloaded |
| Full packaged `.app` launch and Quit | VERIFIED_WORKING | Isolated root migrated to `0008`; desktop and sidecar processes exited |
| English/Hebrew translation contract | VERIFIED_WORKING | Translation-key checker and React RTL tests passed; no manual visual claim |
| External-network audit | PARTIAL | Product Self-Test reported no external network; packet-level capture was not performed |
| Apple signing/notarization | IMPLEMENTED_NOT_RUNTIME_VERIFIED | Development package is unsigned and Gatekeeper rejection is expected |

## Fixes made during packaged acceptance

- Added Demo-only crash injection at four durable transaction boundaries.
- Restricted crash injection to `MELLOWYAK_DEMO_TEST_MODE=1`, a valid synthetic Demo record, and
  its marker file. The route is excluded from OpenAPI and cannot target a normal project.
- Added a read-only Demo Lab status route so restart recovery can be inspected without database
  access from the validator.
- Extended `scripts/validate_packaged_phase8.py` to terminate the packaged sidecar, restart it,
  verify rollback identity, preserve unrelated sentinels, retain journals, and validate a redacted
  Recovery Bundle.
- Added Cargo release path remapping. Release diagnostics now use `<SOURCE_ROOT>` and
  `<CARGO_HOME>` instead of embedding the builder's absolute user path.
- Added `--no-launch` to the macOS installer so installation can be followed by a launch against an
  explicitly isolated data root.

No new runtime dependency was added.

## Source gates

| Command | Result |
| --- | --- |
| `engine/.venv/bin/python -m pytest -o addopts='' -q` | VERIFIED_WORKING — 162 passed, one upstream Starlette deprecation warning |
| `npm test --prefix apps/desktop` | VERIFIED_WORKING — 16 passed |
| Total automated source tests | VERIFIED_WORKING — 178 passed |
| `engine/.venv/bin/python scripts/check_ui_translation_keys.py` | VERIFIED_WORKING — `UI_TRANSLATION_KEYS_ONLY` |
| `npm run typecheck --prefix apps/desktop` | VERIFIED_WORKING |
| `npm run build --prefix apps/desktop` | VERIFIED_WORKING |
| `ruff check engine scripts` | VERIFIED_WORKING |
| `ruff format --check engine scripts` | VERIFIED_WORKING |
| `cargo fmt --check` | VERIFIED_WORKING |
| `cargo check` | VERIFIED_WORKING |
| OpenAPI export twice | VERIFIED_WORKING — identical SHA-256 `f4411a51e2c2e75ab48c67d97565569f1d07d40b5a7a5c738f8381c6bd2da3a0` |
| Migration matrix: empty and `0001`–`0007` to head | VERIFIED_WORKING — every case reached `0008_validated_repair_apply` |

## Fresh package

Build commands:

```text
engine/.venv/bin/python scripts/stage_browser.py
engine/.venv/bin/python scripts/dev.py package
```

Build completed on 2026-08-25 at 06:44 +03:00.

| Artifact | Path | Size | SHA-256 |
| --- | --- | ---: | --- |
| App | `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app` | 721,596 KiB | bundle identity represented by component hashes below |
| Desktop executable | `MellowYak.app/Contents/MacOS/mellowyak-desktop` | 22,632,096 bytes | `7a38e0ca46784a6b921e3d2252121e2b71811567a3a9e8a7a9b703a654f5204c` |
| Engine sidecar | `MellowYak.app/Contents/MacOS/mellowyak-engine` | 75,229,248 bytes | `d5685a5e4ce4c49626e877421d5cb0ad1987224d95fdf376083b659982ffae14` |
| Packaged browser tree | `MellowYak.app/Contents/Resources/browser` | 623,348 KiB | tree digest `e49bacdbdf9904896aa7554cf8b6738be0f88a4aca5972466b14e1b5f9a13bb0` |
| DMG | `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg` | 389,003,357 bytes | `2a33da7fba14f16aaa07880dcab1f039753c2acc1f0c4f03a83b04f9368190d2` |

Package inspection found the desktop executable, engine sidecar, icon, Chromium runtime,
browser manifest, embedded English/Hebrew tray resources, Demo Lab, Product Self-Test, and all
migrations through `0008`. The packaged schema check proves the frozen engine can load and execute
the migration resources. Scans found no local database, snapshot, Repair Workspace, Apply journal,
Recovery Bundle, private updater key, PEM private key, operator credential, real source, or absolute
builder path in the app bundle.

## DMG validation

`hdiutil verify` returned a valid checksum. The image mounted at a unique temporary mount point with
`-readonly -nobrowse`. The mounted desktop and engine hashes matched the app-bundle hashes above,
the icon and browser manifest were present, and the `Applications` link resolved to `/Applications`.
The volume detached cleanly and the mount point was removed.

`codesign -dvvv` reported that the app is not signed. `spctl` rejected it with `no usable signature`.
This is the expected unsigned development state and is not represented as notarized.

## Packaged Demo, Apply, rollback, and recovery evidence

Validator command:

```text
engine/.venv/bin/python scripts/validate_packaged_phase8.py \
  apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app/Contents/MacOS/mellowyak-engine \
  --output /tmp/mellowyak-phase8-final.json
```

Final result: `VERIFIED_WORKING`.

- Nine synthetic Demo Labs were used.
- One invalid candidate was rejected.
- One stale-source Apply was rejected without a write.
- One valid candidate committed after live verification.
- One deterministic post-Apply failure rolled back byte-identically.
- Four abrupt sidecar exits returned the dedicated exit code `86` and recovered after restart:
  `after_journal_before_first_write`, `after_first_file_operation`,
  `after_all_writes_before_post_verify`, and `during_rollback_after_first_restore`.
- Every crash case ended `ROLLED_BACK`, restored `checkout.py` byte-identically, preserved an
  unrelated sentinel byte-identically, retained a non-empty journal, and left no pending recovery.
- One externally altered crash fixture stopped at `FAILED_RECOVERY_REQUIRED`, created a CRITICAL
  local alert, and created exactly one Recovery Bundle containing transaction, journal, safety,
  affected-path, current-hash, expected-hash, and diagnostic records.
- The Recovery Bundle scan found neither the bearer-token canary nor the temporary absolute path.
- No real project was connected or modified.

Measured packaged-sidecar timings:

- cold startup: 28.775390 seconds;
- restart startup: 18.370596 seconds;
- candidate generation and validation: 0.015032 seconds;
- Apply and post-verification: 0.077689 seconds;
- failed post-verification and rollback: 0.089045 seconds;
- Product Self-Test: 0.020510 seconds.

## Full application and installed application

The complete `.app` was launched directly with a new `MELLOWYAK_DATA_ROOT`. It created one
installation identity, migrated to `0008`, bound the engine to loopback, and quit cleanly through
the macOS application Quit event. No desktop or engine process remained.

The previous installed application was preserved as:

`/Applications/MellowYak-previous-20260825-065422-463e83.app`

The validated app was installed at `/Applications/MellowYak.app`. Installed hashes match the fresh
bundle:

- desktop: `7a38e0ca46784a6b921e3d2252121e2b71811567a3a9e8a7a9b703a654f5204c`;
- engine: `d5685a5e4ce4c49626e877421d5cb0ad1987224d95fdf376083b659982ffae14`.

The installed app was launched once with a second isolated data root, reached migration `0008`,
then quit cleanly. No process remained.

## Limitations

- Signing, Hardened Runtime, notarization, and stapling are `IMPLEMENTED_NOT_RUNTIME_VERIFIED`
  because no Apple credentials were supplied.
- Real macOS notification-click interaction is `IMPLEMENTED_NOT_RUNTIME_VERIFIED`; this report
  does not claim a manual click occurred.
- Packet-level external-egress capture is `PARTIAL`; the local Self-Test's no-network step passed,
  and the package exposes only the authenticated loopback product API during this validation.
- Windows, Linux, and Apple Silicon package runtime behavior is `UNKNOWN` in this Intel macOS run.
