# Phase 5 verification, regression gate, and repair validation report

Date: 2026-08-24  
Platform actually verified: Intel macOS (`x86_64`)  
Branch: `product/verification-regression-gate`  
Base commit: `408375978194c48180e5cc1c0885031dcaaf7b7b`  
Migration: `0005_verification_regression_gate`

## Verdict

Phase 5 is verified locally on the supported Intel macOS platform. MellowYak selects a current required Protected Behavior, replays its accepted flow in packaged Chromium, observes the seeded PulsePlan `15:00 IDT` regression against expected `14:00`, stores separate current evidence, records a supported regression, blocks completion, creates a deterministic local Repair Context, detects a repaired source identity, marks the old gate stale, re-verifies `14:00 IDT`, resolves the original finding, records VERIFIED_COMPLETE, restarts, and reloads the complete history.

This verdict does not cover Windows, Linux, Apple Silicon, signing, notarization, connector enforcement, arbitrary local commands, CI execution, or public release.

## Automated source results

- Python: **106 passed** (`engine/.venv/bin/pytest -q`), one upstream Starlette/httpx deprecation warning.
- React/Vitest: **12 passed** (`npm --prefix apps/desktop test -- --run`).
- Total: **118 passed**.
- Ruff check and format check: passed.
- UI translation-key-only check: `UI_TRANSLATION_KEYS_ONLY`.
- TypeScript/Vite production build: passed.
- `git diff --check`: passed.
- OpenAPI generation and TypeScript client generation: passed.
- OpenAPI SHA-256: `47d191b6f4eeb8b32fbfbb06dff888fb4f25ffe9dd7a137d25c03d5e170ef29e`.

## Packaged Phase 5 evidence

Validator: `scripts/validate_packaged_phase5.py` against the engine inside the freshly built `.app`.

- schema: `mellowyak.phase5_packaged_validation.v1`
- status: `VERIFIED_WORKING`
- startup: 25.484 seconds (cold packaged sidecar)
- failed run: `3c961e30-739e-4866-a69f-c7b2b58bc687`, 1.975 seconds
- expected/observed: `14:00` / `15:00 IDT`
- baseline bundle: `a065f426-d128-4243-8d5a-82abeb572cc9`
- separate failed current bundle: `970b6f05-4be3-4811-8007-12338cc10947`
- regression: `e26fade1-c00b-474c-bf48-fa33ab74c9d2`
- blocked gate: `e9f5ab12-f2d0-41ec-942e-59810a7eb3d4`
- Repair Context: `44819cd0-168a-44af-85f2-3b17a26378cc`
- Repair Context digest: `eef319bc1ec51f821ee1190be6ff099c11176c8f0485993ffdc31dfb229e300c`
- repaired run: `bfceaaa3-a1b3-4ca8-b87d-323ee7e7d21b`, 1.939 seconds
- verified gate: `d2fc5359-aa97-4b5c-a619-9df4823aa4a1`
- restart/history reload: passed
- loopback/auth checks: passed
- source/evidence upload: false
- Repair Context transmission: false
- orphan engine/browser process: false

Identifiers above belong only to the disposable packaged validation data root and contain no user project data.

## Packages and hashes

- `.app`: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app` — 719,180 KiB allocated (about 702.32 MiB).
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg` — 387,369,236 bytes (about 369.42 MiB).
- DMG SHA-256: `5e28c6357c9d94b6b4eaf66c4dc498c9997c4e5b8b68d011de45c8d70e101728`.
- desktop executable: 20,472,924 bytes; SHA-256 `f5c22bbb7a92e2286f0ad4567ae657bb92659f0801832a82ca5d0dc703c2f138`.
- engine executable: 74,920,320 bytes; SHA-256 `2614f17c8986747def868b654f4ebc38c56594f59977137bf2b0a1b75355998c`.
- Chromium 151.0.7922.34 framework: 255,906,780 bytes; SHA-256 `a2915e6591134b56ee281c34bc4193d49c4422c283a2b75c10b64cf646367552`.

The DMG checksum verification, read-only mount, `.app` presence, Applications link, and unmount passed. The local app was installed at `/Applications/MellowYak.app`; the prior copy remains recoverable at `/Applications/MellowYak-previous-20260824-184747-03fdb4.app`.

## Release, CI, and updater state

The unpublished local package is unsigned and unnotarized. A release-config build correctly refused to create a signed updater archive because no private signing key was available; a normal unpublished `.app` and DMG build then completed. No release was published. The updater public-key configuration and signed-release workflow remain present, but a signed end-to-end update was not runtime verified.

Linux and Windows package matrices now build from the same commit, and macOS CI invokes the Phase 5 packaged validator. These workflows were edited and syntax-reviewed locally; they were not executed by GitHub Actions in this local-only task. Windows, Linux, and Apple Silicon remain unverified.

## Honest limitations

Browser Replay is the only automated adapter. Human attestation is explicit. A general local-command runner, AI visual comparison, connectors, external gate enforcement, automatic repair, automatic baseline replacement, accounts, cloud synchronization, source upload, evidence upload, analytics, token savings, and financial claims are absent. VERIFIED_COMPLETE covers only required checks in the exact current known Protection Plan.
