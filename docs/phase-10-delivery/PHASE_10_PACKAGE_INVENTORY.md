# Phase 10 package inventory

Version: `0.2.0-preview.1`
Platform: Intel macOS x86_64
Status: local unsigned Technical Preview evidence

| Component | Size | SHA-256 |
|---|---:|---|
| `MellowYak.app` | 721,728 KiB | directory; executable hashes below |
| `mellowyak-desktop` | 22,722,824 bytes | `f29d89ad283238376bbddaa26abef9ec0c5cf18f2fd4f2f85075271d3287a138` |
| `mellowyak-engine` | 75,282,096 bytes | `bd906b599fa68d4edc83a9c69eb34f213251a0c14ec6175d8c6f716446a02d18` |
| Browser runtime | 623,348 KiB, 336 files | contained in application resources |
| `MellowYak_0.2.0-preview.1_x64.dmg` | 389,109,699 bytes | `2b43debaaa4b2ec11bf585b0f42693ada35fcf80c0b8d23d108171fe579fb8c8` |

Build application: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
Build DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.2.0-preview.1_x64.dmg`
Installed application: `/Applications/MellowYak.app`

The installed executable hashes equal the build and read-only DMG hashes. The recoverable previous
installation is `/Applications/MellowYak-previous-20260825-145112-84c336.app`.

The package scan found no absolute home build path, supplied password, private-key marker or persisted
session-token assignment. The artifact is unsigned/unnotarized and must not be published as a trusted
release.
