# Phase 10 Product Truth and Daily Workflow validation report

Date: 2026-08-25
Branch: `product/product-truth-daily-workflow`
Starting commit: `699add76f61d05cb38e86541a7a193b8f459a06b`
Version: `0.2.0-preview.1`
Current-platform decision: **VERIFIED_WORKING on Intel macOS x86_64**

## Result

Phase 10 replaces acceptance-only presentation with evidence-bound daily product surfaces. Home,
Project Overview, Activity, Episode Detail, Regression Detail and Diagnostics are backed by bounded,
typed, project-isolated aggregates over existing Phase 1–9 records. First Run is an actual persisted
selection flow. Repair, candidate validation, deliberate Apply, rollback, disconnected projects,
support, updater and activity modes retain their existing safety boundaries and are now presented as
operational states.

No database migration was required. Schema `0009_technical_preview_readiness` remains authoritative.
No dependency or license file changed. No APC file, real project, cloud service, model/provider API,
account, source upload, analytics endpoint, Git push or public release was used.

## Exact source gates

| Gate | Exact result |
|---|---|
| Python | 170 passed; 1 upstream Starlette/httpx deprecation warning; 77.42 s |
| React | 22 passed; 20.5 s; one non-failing controlled/uncontrolled warning in the synthetic First Run test |
| Automated source total | 192 passed |
| TypeScript | passed |
| Vite production build | passed; JS 591.08 kB, 153.93 kB gzip; advisory above 500 kB |
| UI localization policy | `UI_TRANSLATION_KEYS_ONLY` |
| English/Hebrew parity and RTL | passed |
| Ruff check/format | passed |
| Cargo format/check | passed |
| OpenAPI determinism | two exports matched; SHA-256 `e8c0b9d83ec83702ad97afadd8aba2c3e935f43db32c80db009ffdf71867a646` |
| Migration matrix | empty plus each predecessor 0001–0008 upgraded to 0009; 9 cases passed |
| Diff whitespace | passed before delivery finalization; repeated in the final Git gate |

## Packaged gates

- Phase 8 packaged validator: `VERIFIED_WORKING`; 9 Demo Labs, 22 Self-Test steps, one committed
  Apply, one byte-identical post-check rollback, one stale-source pre-write block, four byte-identical
  crash recoveries, redacted recovery evidence, no network and zero orphans.
- Phase 9 packaged validator: `VERIFIED_WORKING`; clean install, first-run persistence/replay,
  schema-0009 upgrade preservation, disconnected project, identity-safe reconnect/relocate,
  notification route rejection, private tray/diagnostics, redacted support bundle, updater fixtures,
  activity-mode persistence and source immutability passed.
- Phase 10 packaged validator: `VERIFIED_WORKING`; empty and populated Home, Project Overview,
  Activity, Demo Lab regression, invalid/valid candidate, Apply, rollback, Product Self-Test,
  Diagnostics privacy, no product egress, no pending recovery and reset passed.
- Regression Detail is package-reported as `UNIT_VERIFIED_WITH_PROJECT_ISOLATION`: its typed route and
  cross-project rejection are source-tested, while the disposable Demo Lab does not persist a real
  `RegressionFinding` record solely to turn that unit evidence into a packaged UI claim.

## Package and native lifecycle

| Artifact | Size | SHA-256 |
|---|---:|---|
| macOS application | 721,728 KiB | executable identities below |
| Desktop executable | 22,722,824 bytes | `f29d89ad283238376bbddaa26abef9ec0c5cf18f2fd4f2f85075271d3287a138` |
| Engine executable | 75,282,096 bytes | `bd906b599fa68d4edc83a9c69eb34f213251a0c14ec6175d8c6f716446a02d18` |
| Browser runtime tree | 623,348 KiB; 336 files | packaged local runtime |
| DMG | 389,109,699 bytes | `2b43debaaa4b2ec11bf585b0f42693ada35fcf80c0b8d23d108171fe579fb8c8` |

The DMG checksum passed, mounted read-only, contained the correct application and `/Applications`
link, matched both executable hashes and detached cleanly. The installed application under
`/Applications/MellowYak.app` matched both hashes, reached schema 0009 with isolated data, rejected a
second instance without creating a second data root, and explicit Quit left zero desktop/engine
orphans. Observed idle use was 0.1% combined CPU and 224,724 KiB combined RSS. Packaged Phase 8
measured 20.336944 s cold startup and 20.098660 s restart startup.

The local package is unsigned and unnotarized. `codesign --verify` returned 1 and `spctl` returned 3
with `no usable signature`; this is an explicit release limitation, not a signed distribution claim.

## Visual delivery

Thirty-six deterministic synthetic screenshots, a JSON manifest, Markdown/HTML guide and an
8,523,134-byte PDF are under `docs/phase-10-delivery`. The PDF SHA-256 is
`910eb6083bac4e350200a6155f03b439a3ecf26b28ae424e27993cd7517c9758`. English operational states and
Hebrew RTL states were visually inspected. The web tray image is explicitly test-only; the actual
tray is native Tauri/Rust UI.

## Platform and release boundary

Intel macOS x86_64 is the only runtime-accepted Phase 10 platform. macOS Apple Silicon, Windows x64
and Linux x64 share the same source, API, schema and version and have pinned build/validation wrappers;
they are **configured, not runtime verified**. The new Windows acceptance workflow has not run in this
local session. Production signed updater delivery, code signing, notarization and a real-project
operator run remain unverified. No tag may be described as a public release.
