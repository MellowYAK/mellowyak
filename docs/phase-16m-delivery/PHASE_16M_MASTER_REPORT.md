# MellowYak Phase 16M-C Closure Report

## Current verdict

- Product verdict: `INTEL_MAC_TECHNICAL_PREVIEW_ACCEPTED_WITH_LIMITS`.
- Automated/functional Mac closure: `CLOSED`.
- Human physical verdict: `DEFERRED_POST_PREVIEW`.
- Distribution verdict: `PUBLIC_MAC_DISTRIBUTION_BLOCKED`.
- Windows x64 port: `AUTHORIZED` from the frozen shared-source checkpoint.
- Linux x64 and Apple Silicon: `NOT_YET_NATIVELY_ACCEPTED`.
- Phase 17: not started by this closure.
- Source checkpoint tag: `phase-16m-intel-mac-technical-preview-accepted-with-limits-2026-08-28`.

Human-only OS-transition acceptance was deliberately deferred by the operator. This does not change the automated or functional evidence and does not imply public Mac distribution readiness.

## Exact candidate identity

- Version: `0.5.0-preview.3`.
- Branch: `product/intel-mac-product-lock`.
- Final build commit: `a24d9f7e252c71f4d389493988ffd38075783807`.
- Database head: `0011_baseline_lock_and_local_proof`.
- Application: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`.
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.5.0-preview.3_x64.dmg`.
- Installed application: `/Applications/MellowYak.app`.
- Desktop executable SHA-256: `2f798f787be42df85072812b33daf860b26789d5885f8f3bfd5f4d4adf168159`.
- Engine SHA-256: `ea492adad0b4239b6e4ba5c7ed998d55c4e0dd883d484511202b0b1f49cb8e2e`.
- Browser launcher SHA-256: `97136324f0a487d9fef8eee50341a1b433a05bc4228daae5b1ac19d18ff068fb`.
- Final signed DMG SHA-256: `ada29bfe1c9887256f057279ee7e201cad0ea6db3a379bb980a6466ffe3ce7dd`.
- Deterministic OpenAPI SHA-256: `608ced66dbc65676ab44abae5ed97f070b1ee41af7fc7db127fa35623a66949f`.

## What changed in Phase 16M-C

1. Notification activation now revalidates its destination at click time. A stale or rejected route safely opens Alerts instead of navigating to invalid project context.
2. A React regression test covers the stale-notification fallback.
3. Finder Alias relocation and reconnection were completed against the installed application. The original project ID and history were retained, and a mismatched directory was rejected without changing the stored source.
4. Quiet Mode was exercised against a real alert in the isolated acceptance database. The in-app alert remained available while native delivery was suppressed; Quiet Mode was then ended and restored to off.
5. The default product window remains the user-approved `1220 × 820` size.
6. The Intel application and DMG were rebuilt at `0.5.0-preview.3`, ad-hoc signed, installed, and hash-matched.
7. Privacy-exposing Settings captures were removed from the delivery directory. Canonical crops contain only the MellowYak notification pane.
8. Documentation now uses the multi-axis evidence model instead of conflating automation, visual evidence, and human physical actions.
9. Native automation found that disabling close-to-tray left the tray process and engine alive. The close handler now performs an explicit clean exit when that policy is disabled; a Rust regression test and installed-app process retest prove the repair.

## Source and package verification

- Python: `211 passed`; one benign third-party Starlette deprecation warning.
- React/Vitest: `30 passed`.
- TypeScript, Vite, translation-key-only UI check, English/Hebrew parity, Hebrew RTL, Ruff, Cargo format, and Cargo check: PASS.
- Migrations: empty database plus every 0001–0010 input migrated to 0011 with preserved data.
- OpenAPI: two byte-identical exports.
- Phase 8, 9, 10, 11M, 12, 13, 14, 15, lifecycle, and updater packaged validators: `VERIFIED_WORKING`.
- Phase 11M initially exposed an unsigned outer DMG. The DMG was signed and the validator was rerun successfully; the hash above is the corrected final artifact.
- Native lifecycle: clean launch, single instance, one engine, supervised engine restart, explicit exit, and owned-child cleanup passed.
- Updater E2E: success path and tamper/wrong-key/incomplete/downgrade rejection passed using ephemeral acceptance keys while durable data and project identity remained preserved. Production update signing remains unconfigured.
- No external product network was observed during the packaged verification.

## P15-PHYS closure highlights

- P15-PHYS-120: installed-app positive Finder Alias reconnect PASS; foreign-source mismatch rejection PASS; one project record and the same project ID remained.
- P15-PHYS-112: source implementation and automated regression PASS; a complete human click of a delivered notification after making its destination stale remains `HUMAN_PHYSICAL_NOT_RUN`.
- P15-PHYS-127: installed-app Quiet Mode state, in-app alert persistence, and restoration PASS; a human-observed before/after native banner sequence remains `HUMAN_PHYSICAL_NOT_RUN`.
- Logout/login, lock/unlock, sleep/wake, restart, and real battery transition remain honestly pending.

## Localization contract

All GUI copy must be referenced through translation keys. English is the base catalog, Hebrew has matching keys and renders RTL. The source checks and React tests passed for this candidate. Additional languages can be added as new catalogs without changing component copy.

## Security and privacy

- The public repository receives no user database, project source, browser profile, credential, token, private support bundle, or acceptance data root.
- All acceptance work used a disposable project and an isolated `/private/tmp` data root.
- Normal user data was not used as test data and was not modified.
- Deterministic screenshots are explicitly labeled as product-view evidence, not human physical evidence.
- Reused unchanged screenshots retain their original per-image capture commit and app hash; these are provenance metadata and do not conflict with the reconciled final candidate identity.
- Ad-hoc signing is suitable only for local technical-preview acceptance. It is not a substitute for Developer ID signing and notarization.

## Reports

- `PHASE_16M_EXECUTION_AND_EVIDENCE_REPORT.md` and `.pdf`: complete technical execution, provenance, verification, evidence axes, cleanup, and verdicts.
- `PHASE_16M_VISUAL_MANUAL_AND_CHECKLIST.md` and `.pdf`: English operator manual containing the canonical screenshots and an explanation of every represented page.
- `PHASE_16M_PHYSICAL_ACCEPTANCE.md`: per-test multi-axis matrix for P15-PHYS-101 through P15-PHYS-128.
- `PHASE_16M_EVIDENCE_MANIFEST.json`: machine-readable evidence schema `mellowyak.phase16m.acceptance-evidence.v2`.

## PDF quality gate

- Execution report: 9 pages, 330,140 bytes, SHA-256 `3216caa1910c7d2ff31c5304f863bfdd7e2a26c9ecee0a78c0ffde3cb24403e0`.
- Visual manual: 55 pages, 12,283,935 bytes, SHA-256 `4ee4ddcd85e527db1de9658552d080864c2aca19be4e1716779829ba4e2b0034`.
- Both closure PDFs were regenerated and rendered successfully after the handoff verdict update. The modified verdict pages, final matrix page, images, page numbers, and privacy boundaries passed inspection.

## Exact next authorized action

Use the annotated source checkpoint for native Windows x64 implementation. The deferred Mac workbook remains available for later post-preview hardening; its rows remain `HUMAN_PHYSICAL_NOT_RUN`. Do not treat this handoff as Phase 17 implementation on macOS.


## Complete acceptance-axis cross-reference

| Test ID | Native automation | Human physical | Visual | Functional | Cleanup |
|---|---|---|---|---|---|
| P15-PHYS-101 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-102 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-103 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NO_VISUAL_EVIDENCE_REQUIRED | PASS | PASS |
| P15-PHYS-104 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-105 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-106 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-107 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-108 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-109 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-110 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-111 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-112 | BLOCKED | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-113 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-114 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | PASS |
| P15-PHYS-115 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-115B | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | PASS |
| P15-PHYS-116 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | PASS |
| P15-PHYS-117 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | PASS |
| P15-PHYS-118 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | PASS |
| P15-PHYS-119 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-120 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-121 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-122 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-123 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-124 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-125 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | PASS |
| P15-PHYS-126 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | PASS |
| P15-PHYS-127 | BLOCKED | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | PASS |
| P15-PHYS-128 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | PASS |
