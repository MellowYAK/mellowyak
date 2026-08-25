# Phase 10 exact verification evidence

## Source identity

- Branch: `product/product-truth-daily-workflow`
- Starting commit: `699add76f61d05cb38e86541a7a193b8f459a06b`
- Version: `0.2.0-preview.1`
- Database head: `0009_technical_preview_readiness`
- Phase 10 migration: none
- Dependency/license changes: none

## Source results

| Gate | Result |
|---|---|
| Python | 170 passed, 1 upstream deprecation warning, 77.42 s |
| React | 22 passed, about 20.5 s |
| Total | 192 passed |
| TypeScript / Vite | passed / passed |
| UI translation policy | `UI_TRANSLATION_KEYS_ONLY` |
| Hebrew parity and RTL | passed |
| Ruff / Cargo | check and format passed |
| OpenAPI | deterministic SHA-256 `e8c0b9d83ec83702ad97afadd8aba2c3e935f43db32c80db009ffdf71867a646` |
| Migrations | empty plus 0001–0008 to 0009: 9 cases passed |

Vite reported one advisory: the 591.08 kB minified JS chunk exceeds 500 kB (153.93 kB gzip). React
emitted one non-failing controlled/uncontrolled warning only in the synthetic First Run test.

## Package results

Phase 8, Phase 9 and Phase 10 JSON validators all report `VERIFIED_WORKING`. Exact JSON is adjacent to
this report. Phase 8 measured 20.336944 s cold startup and 20.098660 s restart; candidate validation
0.017403 s; Apply/live verification 0.091452 s; rollback 0.102481 s; Self-Test 0.023451 s.

The fresh Intel macOS app and DMG built successfully. `hdiutil verify` returned a valid checksum; the
read-only mount contained the correct application, both executables and `/Applications` link; hashes
matched and detach succeeded. Installed hashes matched. Isolated native launch reached schema 0009,
second launch exited without another data root, explicit Quit left zero orphans, and local idle
observation was 0.1% CPU / 224,724 KiB RSS combined.

The artifact is unsigned and unnotarized: `codesign --verify` exit 1; `spctl` exit 3 with
`no usable signature`.

## Captures

Thirty-six PNG states exist. The PDF is 8,523,134 bytes with SHA-256
`910eb6083bac4e350200a6155f03b439a3ecf26b28ae424e27993cd7517c9758`. The screenshot manifest
SHA-256 is `b579e4c0f2d0bb8513f58fa9a4c3e452a08a463ed5ba97c481dea86c76b01562`.

## CI and platforms

Local source and Intel macOS package gates executed. The Windows acceptance workflow and existing
cross-platform workflows are configured but were not run remotely in this session. Apple Silicon,
Windows and Linux are not runtime verified. No public release, signing/notarization or production
updater acceptance occurred.
