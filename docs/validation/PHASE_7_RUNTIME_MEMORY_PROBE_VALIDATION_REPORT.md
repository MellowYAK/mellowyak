# Phase 7 runtime, memory, and probe validation report

Date: 2026-08-24

Starting branch: `product/desktop-productization-tray-notifications`

Starting commit: `7a02e9d4d01ff68c472f21fa1d1ccca929327fc4`

Safety tag: `phase-6-desktop-productization-handoff-2026-08-24`

Implementation branch: `product/runtime-snapshot-probe-foundation`

Migration: `0007_runtime_snapshot_probe_foundation`

## Verdict

**VERIFIED WORKING LOCALLY.** Every required source gate and the fresh Intel macOS packaged flow
recorded below passed against the final Phase 7 worktree. The package is an unsigned local
development artifact, not a public release.

## Implemented validation scope

The final gate must verify the integrated Phase 1–7 product, including:

- versioned multi-runtime profiles and primary/secondary selection;
- Python and Node execution on supported local runtimes plus an honest PHP contract status;
- Git-backed and non-Git Source Identity v2;
- Episode grouping, incremental deterministic snapshots, integrity, restore, deduplication, and
  reference-safe retention;
- Browser/API/CLI/Process/Test/Manual Probes, cancellation, bounded retry, and Impact selection;
- `WATCH`/`SUSPECTED`/`HIGH`/`CONFIRMED` semantics;
- known-good milestone acceptance and restart persistence;
- isolated Repair Workspace materialization without live-source mutation or secrets;
- authenticated loopback API, English/Hebrew parity, RTL, reduced motion, packaging, and restart.

## Source validation results

| Gate | Exact command | Final result |
|---|---|---|
| Python suite | `engine/.venv/bin/pytest -q` | **PASS — 143 passed, 1 Starlette deprecation warning, 58.30 s** |
| React/Vitest suite | `npm --prefix apps/desktop test -- --run` | **PASS — 12 passed in 1 file** |
| Translation-key-only UI | `engine/.venv/bin/python scripts/check_ui_translation_keys.py` | **PASS — `UI_TRANSLATION_KEYS_ONLY`** |
| TypeScript | `npm --prefix apps/desktop run typecheck` | **PASS** |
| Vite production build | `npm --prefix apps/desktop run build` | **PASS — 75 modules transformed** |
| Ruff | `engine/.venv/bin/ruff check engine/src engine/tests scripts/validate_packaged_phase7.py` | **PASS** |
| Ruff format | `engine/.venv/bin/ruff format --check engine/src engine/tests scripts/validate_packaged_phase7.py` | **PASS — 99 files formatted** |
| Cargo format | `cargo fmt --check` in `apps/desktop/src-tauri` | **PASS** |
| Cargo check | `cargo check` in `apps/desktop/src-tauri` | **PASS** |
| OpenAPI determinism | export twice and compare SHA-256 | **PASS — both exports `16e21f13d2fd7cdfe5e3f2964788e827b4fae88cf5f319540ed3ac57c256f462`** |
| TypeScript contract generation | `npm --prefix apps/desktop run contract:generate` followed by typecheck | **PASS** |
| Migration matrix | upgrade empty and revisions `0001`–`0006` to `0007` | **PASS — covered by the complete suite and focused migration/API run** |
| Packaged engine smoke | `scripts/validate_packaged_phase7.py` against the fresh `.app` sidecar | **PASS — `VERIFIED_WORKING`** |
| `git diff --check` | `git diff --check` | **PASS** |

Required final counts:

- Python: **143**
- React: **12**
- Total: **155**

## Required packaged Phase 7 evidence

Validator: `scripts/validate_packaged_phase7.py` against the engine embedded in the freshly built
application.

| Flow | Required evidence | Final result |
|---|---|---|
| Non-Git restart | connect, scan, snapshot, milestone, probe, restart, reload | **PASS — non-Git identity and history reloaded after packaged-engine restart** |
| Snapshot deduplication | logical bytes, new physical bytes, reused bytes, object reuse | **PASS — 582 logical, 296 physical, 286 reused bytes across two snapshots** |
| Known-good to failure | accepted comparable PASS, current FAIL, retry FAIL, `CONFIRMED` | **PASS — 1 milestone and 1 reproducible confirmed regression** |
| File change only | Episode/Save Point and `WATCH`, no regression notification | **PASS in source tests; no file-change-only confirmation path** |
| Flaky | initial FAIL then PASS, never `CONFIRMED` | **PASS in source tests** |
| Repair Workspace | materialize current snapshot, secrets absent, live source unchanged | **PASS — 1 READY workspace; sensitive fixture excluded; live hashes unchanged** |
| Runtime adapters | Python/Node/PHP/metadata-only adapters and exact platform status | **PASS — real local Python 3.11.5, Node 26.7.0 and PHP 8.5.9 argv probes; Ruby/Java metadata-only contract tests** |
| Cleanup | cancelled/finished child processes and engine restart | **PASS — no packaged validator or smoke process remained** |

Required final measurements:

- packaged cold startup time: **26.297781 s**
- packaged restart startup time: **18.572035 s**
- snapshot throughput: **9,749 logical bytes/s (9.521 KiB/s) for the tiny 582-byte fixture**
- snapshot logical bytes: **582**
- snapshot newly stored physical bytes: **296**
- snapshot reused bytes: **286**
- packaged probe runtime: **79.402 ms known-good; 80.656 ms confirmed failure; 0 ms manual adapter measurement**

## Package evidence

Expected fresh relative outputs (not committed):

- application: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg`

| Artifact | Final size | Final SHA-256 |
|---|---:|---|
| `.app` bundle | **721,484 KiB disk usage (705 MiB)** | not represented by one required bundle hash |
| desktop executable | **22,632,096 bytes** | `2fb4d2c16a3e354c0358e1d91fccb8cbbb006c53824e4891293ab71f5b83e9a6` |
| engine executable | **75,124,144 bytes** | `d44bd7f83ca9262395ff055f13f882781f7ae22ca8ab3a01df37babf5357b86a` |
| packaged Chromium framework | **255,906,780 bytes** | `a2915e6591134b56ee281c34bc4193d49c4422c283a2b75c10b64cf646367552` |
| DMG | **388,916,477 bytes** | `166c4269f5f54317a688908eed528a7f66cec41795a6ef145cfc9c1b99e8182f` |

The DMG must be freshly built, checksum-verified, mounted read-only, inspected for the application and
Applications link, then unmounted. Do not reuse Phase 6 artifact values.

## Security and privacy evidence

The final record must explicitly prove project/data-root confinement, symlink safety, sensitive and
provider-private exclusion, no `.env` value persistence, sanitized argv/events, no-shell execution,
loopback-only probes, cross-project denial, live-source immutability, and the absence of analytics,
coding-agent SDKs, source upload, and evidence upload.

Status: **PASS.** The complete suite and focused hardening tests cover confinement, exclusions,
no-shell execution, evidence sanitization, cross-project denial, authenticated loopback-only APIs,
repair isolation, and the absence of upload/connector behavior. The packaged validator independently
confirmed authentication, loopback binding, sensitive exclusion, no upload, and unchanged live
source hashes.

## Platform and release scope

- Intel macOS current package: **built, launched with an isolated data root, and inspected locally**.
- Windows: workflow-configured; runtime **not verified locally**.
- Linux: workflow-configured; runtime **not verified locally**.
- Apple Silicon: **not verified**.
- PHP executable replay: **verified locally with PHP 8.5.9 CLI using an approved argv probe**.
- signing, notarization, public release, and updater end-to-end: outside Phase 7 and unverified.
- GitHub Actions: configuration is not a remote pass; report the actual run state.

## Completion rule

The required local gates passed. The DMG checksum was valid, its read-only mount contained
`MellowYak.app` and the Applications link, and it unmounted cleanly. The fresh app launched from its
bundle with an isolated data root at migration `0007`. The local commit hash is reported in the final
handoff after the one required commit is created; no push or release is part of this phase.
