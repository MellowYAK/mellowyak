# Phase 4 behavior, evidence, and browser validation report

Date: 2026-08-24

Branch: `product/behavior-evidence-browser-foundation`

Base commit: `3a4a945788fcf908f1560fc3adb8c79e7e2dd317`

Phase 3 annotated tag object: `ca89392534eae18a7887c16aa0a20e7361b1f74a`

Remote: `https://github.com/MellowYAK/mellowyak.git`

Overall supported-platform result: `VERIFIED_WORKING`

The final commit is the commit containing this report. A commit cannot contain its own immutable hash; use `git log -1 --format=%H` after the local commit. The exact hash is also included in the Phase 4 handoff response. Nothing was pushed or released.

## Delivered foundation

- Immutable Protected Behavior versions and explicit lifecycle transitions.
- Project-scoped runtime configurations with explicit-port loopback-only entry URLs.
- Local Chromium capture with bounded actions, observations, screenshots, duration, and startup time.
- Mandatory human review with include/exclude controls before baseline acceptance.
- Content-addressed, SHA-256 verified evidence artifacts, deterministic manifests, deduplication, and reference-safe deletion.
- Revision-bound Last Known Good baselines and auditable revoke/archive operations.
- Exact FILE links from a current change to known behaviors; the UI makes clear that a link is not fresh verification.
- English is the base catalog; Hebrew is complete RTL; product UI copy is translation-key driven.

## Database and limits

Migration: `0004_behavior_evidence_browser`.

The migration adds behavior/version/link, runtime configuration, capture/step/observation, evidence artifact/bundle/member, attestation, Last Known Good baseline, and audit-event persistence. Limits are 500 actions, 1,000 runtime observations, 30 screenshots, 10 minutes per capture, 30 seconds startup timeout, 10 MiB per artifact, 500 MiB per project evidence store, and 250 MiB per evidence bundle.

## Exact automated results

- Python: `68 passed` (`engine/tests`).
- React/Vitest: `12 passed` (`apps/desktop/src/App.test.tsx`).
- Total automated tests: `80 passed`.
- UI translation policy: `UI_TRANSLATION_KEYS_ONLY`.
- TypeScript and Vite production build: passed; 65 modules transformed.
- Ruff on Phase 4 Python scope: passed.
- Cargo formatting and compilation: passed.
- OpenAPI export was deterministic across two runs; SHA-256: `8ed108eb925de6a724a61d50dee2e30dd01bcea867f71a8cc2c982a3ef583e39`.

The Starlette test client emits one dependency compatibility warning; it does not change the passing result.

## Packaged macOS validation

Validated platform: Intel macOS (`x86_64`). The packaged engine launched from the `.app`, started the packaged Chromium runtime against PulsePlan, captured and reviewed evidence, accepted a baseline, stopped without orphan child processes, restarted with the same data, and reloaded the behavior, baseline, bundle, and artifact bytes.

Validator result:

```json
{
  "artifact_content_reload": true,
  "artifact_count": 4,
  "baseline_status": "ACCEPTED",
  "capture_status": "REVIEW_REQUIRED",
  "database_schema": "0004_behavior_evidence_browser",
  "orphan_child_processes": false,
  "restart_baseline_reload": true,
  "schema": "mellowyak.phase4_packaged_validation.v1",
  "source_uploaded": false,
  "status": "VERIFIED_WORKING",
  "verdict_claimed": false
}
```

Final local package evidence:

- App: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`, 719,108 KiB.
- Installed app: `/Applications/MellowYak.app`, 719,108 KiB; engine and desktop executables match the built bundle byte-for-byte.
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg`, 387,306,724 bytes, SHA-256 `506b51f889d18536a921f0572c37032aa67ab1e4117bb2f309e8ae4b415cadd9`.
- Engine sidecar: 74,849,216 bytes, SHA-256 `f759ea6adfde1fa2639984aa70dbedb2675228466178ee13269d425bf350df3d`.
- Desktop executable: 20,472,924 bytes, SHA-256 `67475b9f13458d7ffdbe9f8ed470bc084e2ca9a15780f45952794506306ea673`.
- Packaged Chromium executable SHA-256: `97136324f0a487d9fef8eee50341a1b433a05bc4228daae5b1ac19d18ff068fb`.

## App icon evidence

The supplied character reference was converted with the built-in image-generation workflow into a production square app icon while preserving the character identity, cream fur, black horns, teal glasses, magenta hoodie, and dark navy/teal background. The prompt required centered safe margins, crisp small-size readability, and no text or watermark.

- Master PNG: `assets/brand/mellowyak-app-icon-master.png`, 1,999,615 bytes, SHA-256 `460a33462b4e80d47577b89e3cf0dfe099772f1ab7e54f1a588d9390dacf8635`.
- macOS ICNS: SHA-256 `72d2c96b424907bc3c099938cfa591f864c0a6d1f3b0f35f15b52df06e280ebc`.
- Windows ICO: SHA-256 `befbc358c8ce483a1457d554c1d726a1f1abda5842f283779b385c1fb319138a`.

## Security and privacy evidence

External origins, implicit ports, credentials in URLs, fragments, traversal, symlinks, oversized artifacts, tampered artifacts, and deletion of accepted evidence are rejected by tests. Browser contexts are ephemeral. Cookies, authorization headers, storage state, request bodies, and typed form values are not persisted. Source bytes are not uploaded or stored in evidence. The local API remains loopback-bound and per-launch bearer authenticated.

## Honest limitations

- Visible-browser mode is implemented as the default, while the automated packaged acceptance run used headless Chromium: `IMPLEMENTED_NOT_RUNTIME_VERIFIED` for a manual visible-browser session.
- Screenshots, actions, and bounded network observations are real. Playwright trace and video are disabled and not captured: `PARTIAL` for those optional artifact types.
- Apple Silicon macOS, Windows, and Linux runtime/package execution were not run on this machine: `UNKNOWN`. Workflows and icon assets are present but remote CI was not observed.
- Updater wiring exists, but no newer signed release was installed: `IMPLEMENTED_NOT_RUNTIME_VERIFIED`.
- Signing, notarization, publishing, and GitHub Release creation are outside this phase: `UNKNOWN`.
- Phase 4 does not run assertions, declare PASS/FAIL, detect regressions, select required checks, heal code, or enforce a Completion Gate.

## Corrected execution attempts

The following attempts failed safely and were corrected before acceptance: an obsolete contract-generation script name was replaced by `npm run contract:generate`; two commands were initially run from the repository root instead of the desktop directory; one DMG bundling retry detached its temporary volume before succeeding; the first icon copy used the wrong working-directory-relative path; one new backend assertion read criticality from the wrong response level; the Change Detail React test needed the new behaviors endpoint in its mock; Ruff was first invoked from the wrong directory and later found one obsolete `noqa`; and the first packaged validator invocation used a desktop-relative engine path. None of these attempts changed APC, pushed Git, published a release, or weakened a validation gate.

## Acceptance

The Intel macOS local packaged workflow is `VERIFIED_WORKING`. Phase 4 is complete as a review-first behavior/evidence/browser foundation. The optional trace/video surfaces and untested platforms remain explicitly limited and do not receive stronger claims.
