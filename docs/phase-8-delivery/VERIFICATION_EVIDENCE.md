# Phase 8 verification evidence

This file records the completed automated implementation checks and fresh package build. No Phase 7
package identity is reused. At the operator's instruction, no additional packaged-runtime or DMG
mount/inspection validation was run after the fresh build; those items remain explicitly assigned to
morning manual acceptance.

## Provenance

- Starting branch: `product/runtime-snapshot-probe-foundation`
- Starting commit: `b50b61708089a556dd778e937f9f268184d10b2b`
- Safety tag: `phase-7-runtime-snapshot-probe-verified-2026-08-25`
- Final branch: `product/validated-repair-safe-apply`
- Migration: `0008_validated_repair_apply`
- Final commit: recorded after the single local commit is created.

## Exact results

- Python: **161 passed** in **65.25 s**; one upstream Starlette/httpx deprecation warning.
- React/Vitest: **16 passed** in **16.87 s**.
- Total automated tests: **177 passed**.
- Translation policy: `UI_TRANSLATION_KEYS_ONLY`.
- TypeScript: passed (`tsc --noEmit`).
- Vite production build: passed; 77 modules transformed in 1.16 s in the recorded full gate.
- Ruff check and format check: passed.
- Cargo format/check: passed; Cargo check completed in 1.23 s.
- OpenAPI: generated twice from clean temporary databases; SHA-256 comparison passed.
- Migration matrix: fresh empty database plus upgrades from `0001` through `0007` passed.

## Deterministic Phase 8 evidence

- Candidate manifest tests passed for deterministic ordering/digest, text/binary classification,
  sensitive path rejection, symlink rejection, hard-link rejection, traversal confinement, exact
  digest preflight, and missing-path ADD preflight.
- Confirmation tests passed for exact project/candidate/source binding and mismatch rejection.
- Durable journal reload passed with owner-only `0600` mode and ordered event sequence.
- Demo Lab integration passed for `VALIDATION_FAILED`, `VALIDATED`, `COMMITTED`, stale-source HTTP 409
  with unchanged external bytes, and `ROLLED_BACK` with byte-identical source.
- Product Self-Test passed 22 executed steps: engine, migration, runtime profile, known good,
  confirmed regression, snapshot/deduplication, workspace, candidate manifest, invalid rejection,
  valid validation, safety integrity, journal, Apply, post-verification, rollback, byte identity,
  restart journal load, hashes, no-network, no-orphan, and cleanup.
- Candidate generation, workspace validation, Apply, rollback, and Product Self-Test durations were
  not separately benchmarked in this handoff because the operator requested no further verification
  runs. The implementation records per-step duration during normal execution.
- Full partial-Apply crash recovery and unresolved Recovery Bundle behavior are implemented and
  covered by primitive/journal paths, but packaged end-to-end crash injection was not run after the
  operator stopped further verification. Manual acceptance owns that check.

## Fresh Intel macOS packaging

- Fresh package command elapsed time: **156.17 s**.
- Application: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
- Application disk usage: **721,592 KiB** (738,910,208 bytes by KiB conversion).
- Desktop executable: `MellowYak.app/Contents/MacOS/mellowyak-desktop`
  - size: **22,640,288 bytes**
  - SHA-256: `45fddbbc330b99fb7f5c1a9c17816c7be30cd7600b8abe2e3739bc430ee74428`
- Engine: `MellowYak.app/Contents/MacOS/mellowyak-engine`
  - size: **75,223,936 bytes**
  - SHA-256: `11188bbfa92d048b4f3520da98c106fe9eef3ed856850b7cb61f22de8c11de2f`
- Chromium executable: `MellowYak.app/Contents/Resources/browser/chromium/chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`
  - size: **26,964 bytes** (launcher executable; framework payload is separate inside the app)
  - SHA-256: `97136324f0a487d9fef8eee50341a1b433a05bc4228daae5b1ac19d18ff068fb`
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg`
  - size: **388,996,478 bytes**
  - SHA-256: `ae86f213aed1f22396f25d84f9d4d1d358e5c10c80e157e9fe857b9405353be1`
- Generated application/DMG/sidecar/browser/build output is excluded from the local commit.

The fresh `.app` and DMG built successfully. Per the operator's instruction, packaged-engine smoke,
DMG checksum/mount/content/unmount inspection, cold/restart startup measurement, and packaged Demo
Lab/Apply/rollback/crash-recovery/self-test execution were not run after packaging. The validator
`scripts/validate_packaged_phase8.py` and the guided `MORNING_MANUAL_ACCEPTANCE.md` are included for
the operator.

## Screenshots and documentation

- 26 deterministic synthetic PNG screenshots.
- English-base screens plus three Hebrew RTL critical states.
- Markdown/HTML guide, machine-readable manifest, and a 5,376,038-byte PDF.
- Every screen records purpose, displayed state, synthetic data source, actions, known facts,
  unknowns, next step, and whether the shown live source has been modified.

## Dependencies, CI, and platforms

- Dependency changes: **none**.
- New dependency licenses: **none**. Existing standard-library, FastAPI, SQLAlchemy/Alembic, React,
  Tauri, Playwright, and PyInstaller stack is reused.
- CI workflow state: existing macOS/Windows/Linux workflows remain configured; no remote CI run was
  triggered and no workflow file changed in Phase 8.
- Runtime-verified platform in this handoff: Intel macOS build only; the post-build runtime acceptance
  is pending the manual operator session.
- Unverified: Windows runtime/package, Linux runtime/package, Apple Silicon, signing, notarization,
  public updater delivery, production deployment, and external-database isolation.
