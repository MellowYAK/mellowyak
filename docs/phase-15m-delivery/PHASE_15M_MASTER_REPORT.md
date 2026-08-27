# MellowYak Phase 15M Master Report

Completion date: 2026-08-27 (Asia/Jerusalem)

## Executive result

Phase 15M implements the approved Intel Mac differentiation cut: Baseline Lock, Expected Change reverification and proven promotion, immutable Known-Good lineage, plain-language Verified Repair Contract states, and immutable local Yak Receipts. Source, migration, package, updater, installation, and automated native-lifecycle gates are green on Intel macOS.

The primary result is **`INTEL_MAC_PRODUCT_LOCK_BLOCKED_WITH_EVIDENCE`** because a human operator was not present for the mandatory physical clicks and disruptive OS transitions. The distribution result is **`PUBLIC_MAC_DISTRIBUTION_BLOCKED`** because Developer ID signing and notarization are not configured. This report does not convert automation, Accessibility scripting, deterministic screenshots, or source inspection into physical PASS results.

There are zero known open product-lock P0/P1 defects in the automated scope. The optional Protection Map Lite and Five-Minute Teach Flow were deliberately deferred.

## Source and Git provenance

- Repository: `https://github.com/MellowYAK/mellowyak.git`
- Starting tag: `phase-14m-real-world-compatibility-verified-2026-08-26`
- Starting/tag commit: `b978b021a80af3410ef97cf2cf7d0e93dc697597`
- Final working branch: `product/intel-mac-product-lock`
- Product version: `0.5.0-preview.1`
- Database head: `0011_baseline_lock_and_local_proof`
- Final commit: **not created**; the prompt permits the named completion commit only after mandatory physical gates pass.
- Final verified tag: **not created**; physical acceptance and public signing are incomplete.
- Push/release/public updater publication: not performed.
- APC: not modified.
- Unrelated user-owned Finder Alias files under the Phase 5 screenshot folder were preserved and excluded.

The application source is public. No credential, private source, user database, evidence payload, Repair Workspace, browser profile, package artifact, or local absolute user path is included in tracked delivery content.

## Phase 14 foundation and Gate A

The Phase 14 tag and artifact identities matched the recorded foundation before branching. Gate A completed against the verified foundation:

- Python: 208 passed, one deprecation warning at the Phase 14 baseline.
- React/Vitest: 28 passed at the Phase 14 baseline.
- TypeScript, Vite, translation-key rule, English/Hebrew parity, Hebrew RTL, Ruff, Cargo format/check: PASS.
- Migration inputs 0001–0009 and empty database to 0010: PASS with preserved data.
- Phase 8–14 packaged validators, Product Self-Test, updater fixture, explicit Quit, and owned-child cleanup: PASS.
- Phase 14 application, engine, and DMG SHA-256 values matched the prior Phase 14 report.

## Toolchain and host

- Node pin: `.nvmrc` = `22`
- Node: `v22.23.2`
- npm: `10.9.8`
- Python: `3.11.5`
- Rust: `1.98.0`
- Cargo: `1.98.0`
- macOS: `26.5.2` build `25F84`
- Hardware architecture: Intel `x86_64`
- Main display: built-in Retina, 3072×1920
- Accessibility permission at completion: enabled
- Screen Recording permission at completion: unavailable (`false`)

## Gate B initial physical smoke

The installed Phase 14 application was exercised through automated OS Accessibility and lifecycle checks. Native tray labels were readable and redacted; close-to-tray reduced the window count without creating another app or engine; reopening reused the existing instance. These observations are useful runtime evidence, but they are not physical PASS evidence because no human physically clicked the controls and no operator confirmation/screenshot was available.

Initial smoke statuses:

| ID | Test | Status | Actual result / blocker |
|---|---|---|---|
| P15-PHYS-001 | Native tray/menu visibility | IMPLEMENTED_NOT_RUNTIME_VERIFIED | Automated Accessibility opened the native menu and found translated, redacted labels; no human click/screenshot. |
| P15-PHYS-002 | Red close-to-tray | IMPLEMENTED_NOT_RUNTIME_VERIFIED | Automated close and tray reopen reused one instance/engine; no human click/screenshot. |
| P15-PHYS-003 | Explicit Quit from tray | IMPLEMENTED_NOT_RUNTIME_VERIFIED | Automated process-exit cleanup passed; the exact tray click was not human-operated. |
| P15-PHYS-004 | Native notification delivery | IMPLEMENTED_NOT_RUNTIME_VERIFIED | Delivery code and redaction tests exist; Notification Center delivery was not physically observed. |
| P15-PHYS-005 | Notification click | IMPLEMENTED_NOT_RUNTIME_VERIFIED | Safe route validation exists; no real delivered notification was physically clicked. |

No P0/P1 was exposed by the available initial runtime automation, so implementation continued with the physical boundary retained as an explicit blocker.

## Baseline Lock, Expected Change, and proven promotion

Baseline Lock enforces the product law that Yak never silently moves the goalposts.

- An existing Known Good cannot be updated in place or replaced through the legacy direct-accept route.
- The operator must classify a changed behavior as Expected Change, Regression, or Unsure.
- Expected Change requires a non-empty reason bound to the project, behavior, and exact source identity.
- Reverifying runs the exact approved behavior against the current Runtime Profile and current source.
- Only a comparable current PASS can mint a promotion confirmation.
- The token is behavior/source/runtime/run-bound, single-use, and expires after five minutes.
- Source changes, stale/non-comparable results, errors, or token replay block promotion and persist an honest blocked state.
- Promotion creates a new immutable baseline, preserves the previous baseline, and links the new record through `supersedes_known_good_id`.
- Historical Known Goods remain valid immutable lineage roots; no reasons were invented for them.

Targeted tests cover direct bypass rejection, required reasons, stale source with durable blocked state, reverification, deliberate promotion, preserved lineage, and one-time token replay rejection.

## Verified Repair Contract UX

The repair engine was not redesigned. Phase 15 exposes its existing safety contract in plain language and keeps event state authoritative:

- Before Apply: candidate tested away from live source, protected behavior passed, current source matched.
- Apply remains an explicit operator action.
- The UI reports checking, Safety Snapshot creation, transaction preparation, selected-file writes, live recheck, commit, or rollback only after the corresponding event.
- A failed live post-check does not claim success; it reports restoration in progress and only displays byte-identical restoration after verification.
- Technical identifiers remain available behind technical details, while primary copy avoids unproven root-cause or full-project-safety claims.

## Local Proof Receipt

The Yak Receipt is local, immutable, project-bound, Episode-bound, and source-identity-bound.

- One stable receipt is created per terminal Episode.
- Totals distinguish considered, checked, passed, confirmed regression, deferred, runtime unavailable, omitted, and unknown.
- Deferred does not count as checked; unknown remains unknown; stale evidence is not current evidence.
- `source_modified` is true only for an exact committed Apply result.
- Receipt identity/digest is stable across repeated requests and restart.
- Receipt output excludes source bytes, raw evidence, tokens, cookies, headers, private absolute paths, and database paths.
- Tests recompute totals from authoritative records and verify immutability and idempotence.

## Optional feature decisions

- Protection Map Lite: deferred. The mandatory product-lock and physical acceptance boundaries took priority; no percentage or unproven coverage score was added.
- Five-Minute Teach Flow: deferred. Existing onboarding remains unchanged; no timing claim was fabricated.

## Database and API

Migration `0011_baseline_lock_and_local_proof` is substantive. It adds immutable lineage metadata, behavior-change decisions, and Yak Receipt persistence. The migration matrix passed from empty and every 0001–0010 input to 0011 with data preservation. The real installed user database advanced to 0011 and contains the new decision and receipt tables.

New authenticated loopback-only routes:

- `GET /projects/{project_id}/behaviors/{behavior_id}/known-good-lineage`
- `POST /projects/{project_id}/behaviors/{behavior_id}/change-decision`
- `POST /projects/{project_id}/behaviors/{behavior_id}/expected-change/reverify`
- `POST /projects/{project_id}/behaviors/{behavior_id}/known-good/promote`
- project-bound Yak Receipt list/create routes

Ownership, source freshness, authentication, typed schemas, known facts, unknowns, and limitations remain enforced. OpenAPI was exported twice with the same SHA-256:

`d1a6a3deb87c5ab1c900dfaf3a5e52446bc1d738fc0bc39d2ee5e7fee3d6eedc`

## Security and privacy

- Loopback-only authenticated engine communication remains enforced.
- No new model/provider SDK, analytics, account, cloud sync, prompt access, or external product network was added.
- Passive monitoring and receipt generation do not write source.
- Existing Apply remains explicit, source-bound, short-lived, journaled, and transaction-scoped.
- Package scans found no database, project source, evidence state, runtime state, private build path, or forbidden user-data directory in the bundle.
- Public corpus validators reported `no_external_product_network=true`, `no_private_project=true`, `passive_monitoring_source_safe=true`, and zero owned children after Quit.
- `.gitignore` excludes databases, evidence, browser/runtime/user data, captures, Repair Contexts, traces, videos, profiles, build output, packages, and generated executables.

## Localization and accessibility

- Every new visible label, message, button, placeholder, technical fixture label, and mascot alternative uses translation keys.
- `python3 scripts/check_ui_translation_keys.py`: `UI_TRANSLATION_KEYS_ONLY`.
- English and Hebrew key sets have exact parity.
- Hebrew uses the same components with document RTL and LTR technical identifiers.
- The Phase 15 capture mode is English-only documentation, not a second product implementation.
- Semantic headings, labels, status text, visible focus inherited from the product system, keyboard-operable controls, and non-color state labels are retained.
- React tests include all 12 Phase 15 states and unresolved-key rejection.

## Final source tests

| Gate | Actual result |
|---|---|
| Python full source suite | 210 passed, one deprecation warning |
| React/Vitest final suite | 29 passed |
| TypeScript | PASS |
| Vite production build | PASS, 92 modules transformed |
| UI translation checker | `UI_TRANSLATION_KEYS_ONLY` |
| English/Hebrew parity and RTL | PASS |
| Ruff check/format | PASS |
| Cargo format/check | PASS |
| Migration matrix 0001–0011 | `VERIFIED_WORKING`, data preserved |
| Baseline Lock/Yak Receipt targeted tests | 2 passed within the 210-test suite |
| Deterministic OpenAPI twice | PASS, matching SHA-256 above |

## Packaged validation

The exact final packaged engine SHA-256 was used for Phase 8–15 validators:

| Validator | Result |
|---|---|
| Phase 8 packaged | VERIFIED_WORKING, schema 0011 |
| Phase 9 packaged | VERIFIED_WORKING, migrated 0008 fixture to 0011 |
| Phase 10 packaged | VERIFIED_WORKING, Self-Test PASS, Apply COMMITTED, rollback ROLLED_BACK |
| Phase 11M package | VERIFIED_WORKING, all structure/DMG/signature/privacy checks true |
| Phase 12M packaged | VERIFIED_WORKING, all 23 workflow checks true |
| Phase 13M packaged | VERIFIED_WORKING, all 10 policy/restart checks true |
| Phase 14M public corpus | VERIFIED_WORKING, all 32 checks true on Datasette, Excalidraw, Vite, and Tauri disposable copies |
| Phase 15M packaged | VERIFIED_WORKING, all 10 product-lock route/version/schema checks true |
| Product Self-Test | PASS within packaged validators |
| Updater E2E 0.4.0-preview.1 → 0.5.0-preview.1 | VERIFIED_WORKING, all 22 checks true |
| Automated installed-app lifecycle | VERIFIED_WORKING, all 8 automated checks true |

The updater test used an ephemeral key and local fixture. It rejected tampering, wrong keys, incomplete downloads, and downgrade, preserved durable database/project identity, and left zero engine orphans. It does not publish or validate the production updater channel.

## Final application and DMG

| Artifact | Identity |
|---|---|
| Installed app | `/Applications/MellowYak.app`; 869,064 KiB on disk; version `0.5.0-preview.1` |
| Desktop executable | 22,964,768 bytes; SHA-256 `4244fb81fd941d1d41b8a410b153b3d8dd35133920cac848c79dbedc9a394d57`; Mach-O x86_64 |
| Packaged engine | 15,812,960 bytes; SHA-256 `60d4a9e1e2c08af1d8f412172648d9c314608709d868ae66dd23e446f8b340b3`; Mach-O x86_64 |
| Browser | Google Chrome for Testing `151.0.7922.34`; 623,316 KiB bundle; launcher SHA-256 `97136324f0a487d9fef8eee50341a1b433a05bc4228daae5b1ac19d18ff068fb`; x86_64 |
| DMG | `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.5.0-preview.1_x64.dmg`; 398,862,219 bytes; SHA-256 `83e7b4c2dc319ed955ce5f827af1ef9bc5cba34db24f7438da8526c174e8015c` |

The DMG checksum verified, attached read-only, contained the exact app and Applications link, matched the desktop executable identity, detached cleanly, and was locally ad-hoc signed.

## Installation and automated native lifecycle

The previous installation was preserved recoverably as `/Applications/MellowYak-previous-20260827-021007.app`. The exact app from the verified mounted DMG was copied into `/Applications/MellowYak.app`. Installed hashes match the packaged hashes above. The real local database reports schema 0011.

Automated installed-app results:

- clean launch: PASS;
- exactly one engine child: PASS;
- supervised engine restart after crash: PASS;
- second instance exits and requests focus: PASS;
- no duplicate engine after restart: PASS;
- explicit process exit: PASS;
- child cleanup: PASS;
- final owned MellowYak processes after validation: zero.

## Final physical matrix (Gate E)

Common preconditions: final installed app `0.5.0-preview.1`, schema 0011, Intel macOS 26.5.2, ad-hoc signature, one local user session. Expected behavior is defined by each test name below. Operator confirmation was unavailable. Deterministic screenshots are excluded from physical evidence. Cleanup remained safe; no owned process survived the automated lifecycle suite.

| ID | Physical action and expected result | Actual / evidence | Status |
|---|---|---|---|
| P15-PHYS-101 | Physically open native tray menu; translated/redacted state and actions | Automated AX menu exercise succeeded; no human click or real screenshot | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-102 | Hide/close and physically restore from tray; one instance/engine | Automated AX close/reopen and lifecycle single-instance checks succeeded | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-103 | Second launch from Finder/Spotlight focuses existing app | Automated second-launch check passed; Finder/Spotlight action not human-performed | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-104 | Physically red-close with close-to-tray enabled; monitoring continues | Automated window count changed 1→0 while app/engine remained | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-105 | Disable close-to-tray and physically close; documented policy | Exact physical setting/click not performed | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-106 | Physically Quit from tray; zero children | Automated exit/cleanup passed; tray click not human-performed | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-107 | Physically Quit from application menu; zero children | Automated exit/cleanup passed; menu click not human-performed | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-108 | Notification permission first-run flow and truthful state | Permission UI not physically exercised | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-109 | Permission denied preserves in-app alert and suppresses native delivery | Not physically toggled/observed | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-110 | Permission allowed delivers exactly one native notification | Not physically allowed/observed | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-111 | Physical notification click focuses exact safe route | Safe route validation exists; no real notification click | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-112 | Forged/stale/deleted destination falls back safely | Deterministic route security passed; final physical click unavailable | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-113 | Enable Start at Login and inspect macOS registration | Product/native implementation exists; physical registration not toggled | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-114 | Actual logout/login restores one tray/engine and policy | Requires disruptive operator session transition; operator absent | BLOCKED |
| P15-PHYS-115 | Disable Start at Login and confirm later login does not launch | Exact physical toggle/login not performed | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-116 | Physical lock/unlock preserves one engine/state and no duplicates | Requires operator and locked session | BLOCKED |
| P15-PHYS-117 | Physical idle sleep/wake recovers watcher and tray | Requires operator/power transition | BLOCKED |
| P15-PHYS-118 | Physical sleep/wake with queued safe work is idempotent | Requires operator/power transition | BLOCKED |
| P15-PHYS-119 | Add project through Finder Alias; canonical identity/safe root | Requires physical Finder selection and disposable operator fixture | BLOCKED |
| P15-PHYS-120 | Relocate/reconnect using Finder Alias safely | Requires physical Finder relocation/reconnect | BLOCKED |
| P15-PHYS-121 | Physically mount DMG and drag app to Applications | Automated read-only mount, identity verification, backup, and install passed; no physical drag | BLOCKED |
| P15-PHYS-122 | Cold relaunch from Applications; ready, tray, one engine | Automated installed-app launch/lifecycle passed; no physical Finder launch | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-123 | Physical same-version reinstall without duplication | Exact physical same-version drag/reinstall not performed | NOT_RUN |
| P15-PHYS-124 | Manual uninstall preserves source and documents retained data | Destructive operator action intentionally not performed while operator absent | BLOCKED |
| P15-PHYS-125 | Reinstall after removal restores documented retained data | Depends on P15-PHYS-124 | BLOCKED |
| P15-PHYS-126 | Physical shutdown/restart recovers one engine/scheduler | Requires disruptive operator OS transition | BLOCKED |
| P15-PHYS-127 | Physical Quiet Mode suppresses native delivery but keeps evidence | Product path exists; physical notification observation unavailable | IMPLEMENTED_NOT_RUNTIME_VERIFIED |
| P15-PHYS-128 | Physical Battery Saver defers noncritical browser work | Host state/operator transition not exercised | BLOCKED |

## Screenshot evidence and operator documentation

Direct native screenshot capture was blocked because macOS Screen Recording permission was false. No unrelated windows/private data were captured, and no screenshot was fabricated as physical evidence.

For design/manual review, 24 deterministic screenshots were generated from the final translation-key-backed frontend: 12 Phase 15 states, each captured at the top and again after a smooth human-sized scroll to the bottom. Every image is 1440×1000, English-only, stored in `images/`, embedded and explained in `PHASE_15M_OPERATOR_MANUAL.md`. These are product UI representations—not physical acceptance screenshots.

## Gatekeeper, signing, notarization, and distribution

- Code-sign structure: valid.
- App signature: ad-hoc.
- Team identifier: not set.
- Developer ID identities available: 0 (`NOT_CONFIGURED`).
- Notarization: `NOT_RUN`; no credentials available.
- Stapling: `NOT_RUN`; no ticket present.
- `spctl` Gatekeeper assessment: rejected.
- Production updater signing: `NOT_CONFIGURED`; only ephemeral local E2E keys were used.
- Public distribution ready: false.
- Final distribution result: **`PUBLIC_MAC_DISTRIBUTION_BLOCKED`**.

Local controlled technical use is operational, but `UNSIGNED_TECHNICAL_PREVIEW_READY` is not used as the primary distribution verdict because the mandatory physical matrix is incomplete.

## Product, physical, platform, and unsupported-claim limitations

Product limitations:

- MellowYak protects only explicitly known and actually checked behaviors.
- Impact selects checks; it does not prove causation.
- It does not prove the entire project safe or determine universal root cause.
- UNKNOWN, deferred, unsupported, unavailable, stale, and omitted work remain visible.
- No automatic repair generation or automatic Apply exists.

Physical limitations:

- Mandatory human macOS interactions remain incomplete as listed in Gate E.
- Screen Recording permission prevented real physical screenshot evidence.
- Login/logout, lock/unlock, sleep/wake, Finder Alias, uninstall/reinstall, restart, Notification Center, Quiet Mode delivery, and Battery Saver need an operator session.

Platform limitations:

- Intel macOS: automated source/package/install/lifecycle operational; physical product lock blocked.
- Apple Silicon: NOT_RUN.
- Windows x64: NOT_RUN.
- Linux x64: NOT_RUN.
- No cross-platform readiness is inferred from shared source.

## APC extraction and current architecture

Phase 15 did not copy or modify APC. MellowYak remains a standalone product that previously reimplemented selected APC lessons—local execution, evidence lineage, project/runtime mapping, and transaction concepts—behind its own local-first engine/API/desktop architecture. Baseline Lock and Yak Receipts are native MellowYak capabilities backed by migration 0011 and do not depend on an APC server or APC data.

## Delivery contents

Exactly two primary documents are delivered:

1. `PHASE_15M_MASTER_REPORT.md` — this complete implementation, validation, limitation, and physical-status record.
2. `PHASE_15M_OPERATOR_MANUAL.md` — complete page/operation guide with every Phase 15 screenshot embedded and explained.

The `images/` folder contains the 24 referenced English screenshots. No package binaries or runtime/user data are committed.

## Final verdict and next operator choice

- Product verdict: **`INTEL_MAC_PRODUCT_LOCK_BLOCKED_WITH_EVIDENCE`**.
- Distribution verdict: **`PUBLIC_MAC_DISTRIBUTION_BLOCKED`**.
- Local commit/tag: not created because the mandatory physical gate is incomplete.
- Push/release/public updater: not performed.

The next operator-controlled choice is physical Intel Mac acceptance, then either Developer ID/notarized Intel distribution, a limited unsigned preview decision, Windows x64 work, Apple Silicon work, or launch asset production. Phase 15 stops here.
