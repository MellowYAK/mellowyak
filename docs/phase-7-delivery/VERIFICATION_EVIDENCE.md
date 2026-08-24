# Phase 7 verification evidence

## Status

**VERIFIED WORKING LOCALLY.** These values come from the final Phase 7 source tree and newly built
Intel macOS package; no Phase 5/6 package value was reused.

## Exact source gates

| Gate | Result |
|---|---|
| Complete Python suite | **PASS — 143 passed, 1 deprecation warning** |
| Complete React/Vitest suite | **PASS — 12 passed in 1 file** |
| Total tests | **155 passed** |
| Translation-key checker | **PASS — `UI_TRANSLATION_KEYS_ONLY`** |
| TypeScript | **PASS** |
| Vite production build | **PASS — 75 modules transformed** |
| Ruff check/format | **PASS — 99 Python files formatted** |
| Cargo format/check | **PASS** |
| OpenAPI deterministic export and TS generation | **PASS — `16e21f13d2fd7cdfe5e3f2964788e827b4fae88cf5f319540ed3ac57c256f462` twice; generated contract typechecked** |
| Migration upgrades from empty and `0001`–`0006` | **PASS to `0007_runtime_snapshot_probe_foundation`** |
| Packaged-engine smoke | **PASS — validator status `VERIFIED_WORKING`** |
| Final `git diff --check` | **PASS before final staging; repeated at commit gate** |

## Runtime and snapshot evidence

| Evidence | Exact final value |
|---|---|
| Python adapter status | **Actual local argv execution PASS — Python 3.11.5** |
| Node adapter status | **Actual local argv execution PASS — Node 26.7.0** |
| PHP adapter status | **Contract tests and actual local argv execution PASS — PHP 8.5.9 CLI** |
| Ruby/Java metadata status | **Metadata-only adapter contract PASS; execution intentionally unsupported** |
| Non-Git fixture after restart | **PASS — stable identity and history reloaded** |
| Snapshot logical bytes | **582 across two packaged snapshots** |
| Snapshot physical bytes added | **296** |
| Snapshot reused bytes/objects | **286 bytes reused in snapshot 2** |
| Snapshot throughput | **9,749 logical bytes/s (9.521 KiB/s), tiny fixture only** |
| Episode coalescing evidence | **PASS in complete source suite** |
| Integrity/materialization byte equality | **PASS in source tests and packaged materialization; live hashes unchanged** |
| Reference-safe retention | **PASS in complete source suite** |

## Probe and repair evidence

| Evidence | Exact final value |
|---|---|
| Browser/API/CLI/Process/Test/Manual adapter status | **All six implemented and source-tested; Browser delegates to accepted existing replay; packaged flow exercised CLI and Manual** |
| Packaged known-good PASS identity | **PASS — exact non-Git snapshot/source identity, 1 accepted milestone** |
| Comparable current FAIL and retry FAIL | **PASS — reproducible packaged failure** |
| Final `CONFIRMED` signal/reasons | **PASS — state `CONFIRMED`, 1 confirmed regression** |
| File-change-only `WATCH`, no regression | **PASS in source tests** |
| Flaky FAIL→PASS, not `CONFIRMED` | **PASS in source tests** |
| Probe runtime | **79.402 ms known-good; 80.656 ms confirmed failure; 0 ms manual adapter measurement** |
| Repair Workspace identity/digest | **PASS — 1 workspace in `READY` state, manifest/materialization verified** |
| Live source unchanged | **PASS — before/after hashes identical** |
| Secret scan of workspace/evidence | **PASS — sensitive fixture excluded** |

Use only disposable public fixture identifiers in this document.

## Fresh package evidence

- `.app`: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg`

| Artifact | Size | SHA-256 |
|---|---:|---|
| `.app` bundle | **721,484 KiB disk usage (705 MiB)** | n/a |
| desktop executable | **22,632,096 bytes** | `2fb4d2c16a3e354c0358e1d91fccb8cbbb006c53824e4891293ab71f5b83e9a6` |
| engine executable | **75,124,144 bytes** | `d44bd7f83ca9262395ff055f13f882781f7ae22ca8ab3a01df37babf5357b86a` |
| Chromium framework | **255,906,780 bytes** | `a2915e6591134b56ee281c34bc4193d49c4422c283a2b75c10b64cf646367552` |
| DMG | **388,916,477 bytes** | `166c4269f5f54317a688908eed528a7f66cec41795a6ef145cfc9c1b99e8182f` |

- packaged cold startup time: **26.297781 s**; restart startup: **18.572035 s**
- DMG checksum/mount/inspection/unmount: **PASS — checksum valid; app and Applications link present; clean detach**
- application launch from fresh bundle: **PASS — isolated data root initialized at migration `0007`; clean explicit quit**

## CI, release, and platform state

- GitHub Actions: **workflows configured; no remote Phase 7 run was executed, so not claimed passed**.
- Intel macOS: **fresh local `.app`/DMG build, packaged flow, launch and inspection passed**.
- Windows, Linux, Apple Silicon: **not runtime verified in Phase 7**.
- signing/notarization/public release: **not performed in Phase 7**.
- push: **not performed in Phase 7**.

## Screenshot delivery

- deterministic synthetic screenshots: **23 PNG files, all required names present**
- screen manifest: **23/23 entries with purpose, displayed state, source, actions, known facts,
  unknowns, and next step**
- Hebrew captures: **RTL invariant passed**
- generated guide: **24 pages, 3,956,171 bytes**
- guide SHA-256: `825e51f4f8e097b0e88fc948312ee66710fc053d4e2d856667d6158a309f3332`
- capture invariants: **PASS — no unknown-probe fallback and no cursor/pin artifact in screen 07**

## Git handoff

- final branch: `product/runtime-snapshot-probe-foundation`
- local commit: **created after this evidence; exact hash is reported in the final handoff because a commit cannot contain its own hash**
- required subject: `feat: add runtime profiles snapshot memory and universal probes`
