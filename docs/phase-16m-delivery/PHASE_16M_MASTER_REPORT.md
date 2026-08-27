# MellowYak Phase 16M-C Closure Report

## Current verdict

- Product verdict: `INTEL_MAC_TECHNICAL_PREVIEW_ACCEPTED_WITH_LIMITS`.
- Human physical verdict: `HUMAN_PHYSICAL_ACCEPTANCE_PENDING`.
- Distribution verdict: `PUBLIC_MAC_DISTRIBUTION_BLOCKED`.
- Phase 17: not started and not authorized by this report.
- Local verified tag: not created because human-only boundaries remain pending and P15-PHYS-112/P15-PHYS-127 do not have complete physical activation evidence.
- Repository push: not performed.

## Exact candidate identity

- Version: `0.5.0-preview.3`.
- Branch: `product/intel-mac-product-lock`.
- Final build commit: `71e3955d8a62e546b4a0ac8c34a2fe46f72053b7`.
- Database head: `0011_baseline_lock_and_local_proof`.
- Application: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`.
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.5.0-preview.3_x64.dmg`.
- Installed application: `/Applications/MellowYak.app`.
- Desktop executable SHA-256: `7d21d73deee3c8606e3cdd0aadbee1512bd07ecf6710e5561c9ccbf476aeb0a5`.
- Engine SHA-256: `ea492adad0b4239b6e4ba5c7ed998d55c4e0dd883d484511202b0b1f49cb8e2e`.
- Browser launcher SHA-256: `97136324f0a487d9fef8eee50341a1b433a05bc4228daae5b1ac19d18ff068fb`.
- Final signed DMG SHA-256: `39a4720dcb43ac95eb6ec892f2d4edb169a69c894ff8b516e503ecdd7ae30f73`.
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

## Source and package verification

- Python: `210 passed`; one benign third-party Starlette deprecation warning.
- React/Vitest: `30 passed`.
- TypeScript, Vite, translation-key-only UI check, English/Hebrew parity, Hebrew RTL, Ruff, Cargo format, and Cargo check: PASS.
- Migrations: empty database plus every 0001–0010 input migrated to 0011 with preserved data.
- OpenAPI: two byte-identical exports.
- Phase 10, 11M, 12, 13, 15, lifecycle, and updater packaged validators: `VERIFIED_WORKING`.
- Phase 11M initially exposed an unsigned outer DMG. The DMG was signed and the validator was rerun successfully; the hash above is the corrected final artifact.
- Native lifecycle: clean launch, single instance, one engine, supervised engine restart, explicit exit, and owned-child cleanup passed.
- Updater E2E: success path and tamper/wrong-key/incomplete rejection passed using ephemeral acceptance keys. Production update signing remains unconfigured.
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
- Ad-hoc signing is suitable only for local technical-preview acceptance. It is not a substitute for Developer ID signing and notarization.

## Reports

- `PHASE_16M_EXECUTION_AND_EVIDENCE_REPORT.md` and `.pdf`: complete technical execution, provenance, verification, evidence axes, cleanup, and verdicts.
- `PHASE_16M_VISUAL_MANUAL_AND_CHECKLIST.md` and `.pdf`: English operator manual containing the canonical screenshots and an explanation of every represented page.
- `PHASE_16M_PHYSICAL_ACCEPTANCE.md`: per-test multi-axis matrix for P15-PHYS-101 through P15-PHYS-128.
- `PHASE_16M_EVIDENCE_MANIFEST.json`: machine-readable evidence schema `mellowyak.phase16m.acceptance-evidence.v2`.

## Exact next authorized action

Perform only the remaining human physical tests against this exact installed candidate, record evidence without exposing private desktop content, and then decide whether Phase 16M may receive a local verified tag. Do not begin Phase 17 from this report.


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
