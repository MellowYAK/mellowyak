# Phase 9 package inventory

Version: `0.2.0-preview.1`
Platform: Intel macOS (`x86_64`)
Distribution status: local unsigned Technical Preview evidence

## Final artifacts

| Artifact | Size | SHA-256 |
|---|---:|---|
| Application bundle | 721,696 KiB | tree contains the separately inventoried binaries/browser assets |
| Desktop executable | 22,710,536 bytes | `8b93f7fa635fe4d4f566767536d27d843b8794558978dd56528b1093754d6bdd` |
| Engine sidecar | 75,262,624 bytes | `30f8d77795cff55f6440f2a251ded70a6f1038135150488b80139412bff63fe7` |
| Bundled browser tree | 623,348 KiB | `e49bacdbdf9904896aa7554cf8b6738be0f88a4aca5972466b14e1b5f9a13bb0` |
| DMG | 389,091,955 bytes | `b75f6bae68c42571346ff7bd8e1e61bdd34e28ad8835921e4ada7ff13c638a66` |

Build outputs are intentionally ignored and are not committed. The validated local
paths are the Tauri release bundle's `macos/MellowYak.app` and
`dmg/MellowYak_0.2.0-preview.1_x64.dmg`.

## Phase 8 comparison

| Component | Phase 8 | Phase 9 | Delta |
|---|---:|---:|---:|
| Application bundle | 721,596 KiB | 721,696 KiB | +100 KiB |
| Desktop executable | 22,632,096 bytes | 22,710,536 bytes | +78,440 bytes |
| Engine sidecar | 75,229,248 bytes | 75,262,624 bytes | +33,376 bytes |
| Browser tree | 623,348 KiB | 623,348 KiB | no change |
| DMG | 389,003,357 bytes | 389,091,955 bytes | +88,598 bytes |

No meaningful size reduction was supportable without removing required packaged
browser behavior. The browser tree remains the dominant component. The small Phase
9 growth is accepted because package correctness and Phase 1–8 compatibility remain
verified.

## Installation evidence

- The final application was installed to `/Applications/MellowYak.app`.
- The previous application was preserved under a timestamped
  `/Applications/MellowYak-previous-*.app` recovery path.
- Installed desktop and sidecar hashes equal the final package hashes above.
- The installed app reached schema 0009 against isolated local data and quit with
  zero orphan processes.

## Stale artifact handling

A stale updater archive from 2026-08-24 did not match the final desktop binary and
had no signature. It was removed from the active build output and preserved
recoverably at `/tmp/MellowYak-stale-updater-artifact-20260825.tar.gz`. It is not a
release artifact and is not in Git.

## Package scan

The final bundle/DMG scan found no user home path, updater private key, session token,
real project source, user database, evidence store, support bundle, repair workspace,
or provider credential. The package remains unsigned and unnotarized.
