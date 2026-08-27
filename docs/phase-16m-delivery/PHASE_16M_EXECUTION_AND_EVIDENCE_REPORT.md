# MellowYak Phase 16M — Execution and Evidence Report

## 1. Scope

This is the consolidated English technical report for Phase 16M-C closure on Intel macOS. It records implementation, validation, evidence provenance, limitations, cleanup, and final verdicts. It does not begin Phase 17 and does not convert automated work into human physical evidence.

## 2. Candidate identity

| Field | Value |
|---|---|
| Version | `0.5.0-preview.3` |
| Branch | `product/intel-mac-product-lock` |
| Final build commit | `a24d9f7e252c71f4d389493988ffd38075783807` |
| Database schema | `0011_baseline_lock_and_local_proof` |
| Installed location | `/Applications/MellowYak.app` |
| Platform | Intel macOS, `x86_64` |
| Default window | `1220 × 820` |

## 3. Final artifact identity

| Artifact | SHA-256 |
|---|---|
| Desktop executable | `2f798f787be42df85072812b33daf860b26789d5885f8f3bfd5f4d4adf168159` |
| Embedded engine | `ea492adad0b4239b6e4ba5c7ed998d55c4e0dd883d484511202b0b1f49cb8e2e` |
| Browser launcher | `97136324f0a487d9fef8eee50341a1b433a05bc4228daae5b1ac19d18ff068fb` |
| Signed DMG | `ada29bfe1c9887256f057279ee7e201cad0ea6db3a379bb980a6466ffe3ce7dd` |
| Deterministic OpenAPI | `608ced66dbc65676ab44abae5ed97f070b1ee41af7fc7db127fa35623a66949f` |

The built and installed desktop/engine hashes matched exactly. The DMG path is `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.5.0-preview.3_x64.dmg`.

## 4. Phase implementation

Notification activation was corrected to revalidate a notification route at activation time. If its project, alert, behavior, change, regression, or gate destination has become stale, the installed UI opens the safe Alerts route. A React regression test proves the fallback and prevents the former stale-context navigation behavior.

Native close-policy automation exposed a second shipping defect: disabling “Keep monitoring when the window closes” destroyed the window but left the tray application and engine running. Commit `a24d9f7e252c71f4d389493988ffd38075783807` now maps the disabled policy to an explicit application exit and owned-engine cleanup. A Rust regression test covers all three decisions: hide to tray, quit application, and allow an already-explicit quit. The desktop and DMG were rebuilt from that commit; the repaired installed application closed to zero desktop and zero engine processes when the setting was disabled.

Version metadata was synchronized across the desktop package, Tauri configuration, Rust lockfile, Python engine metadata, OpenAPI metadata, and packaged validators. The final candidate was rebuilt from the exact recorded commit.

## 5. Finder Alias relocation and reconnect

A disposable project was relocated outside the repository. Through the installed application and native folder chooser:

1. The project was disconnected.
2. Reconnect selected a genuine Finder Alias.
3. Canonical resolution found the relocated directory.
4. The original project ID `082d9fa2-95aa-43c3-9178-21ef9a71ba37` and its history were preserved.
5. The database contained exactly one project record.
6. A foreign fixture was then selected and was rejected with: “Project identity does not match. Existing history was not attached and no source was changed.”
7. The valid Alias was selected again and the project returned to Connected.

This closes the automatable and functional axes for P15-PHYS-120 without claiming a human physical click.

## 6. Quiet Mode

Quiet Mode was enabled for one hour in the installed application. A real, eligible warning alert was inserted into the isolated acceptance database. The alert remained visible and actionable inside Alerts while native delivery was suppressed. Quiet Mode was ended, its persisted state returned to inactive, and a second fresh eligible alert exercised the post-quiet path.

macOS Screen Recording permission was unavailable, so no new full-screen capture is presented as physical evidence. The functional axis passes; the human-observed native before/after banner sequence remains pending. Quiet Mode was restored to off and the synthetic alerts were removed during cleanup.

## 7. Source verification matrix

| Check | Result |
|---|---|
| Python tests | PASS — 211 passed |
| React/Vitest | PASS — 30 passed |
| TypeScript | PASS |
| Vite production build | PASS |
| GUI translation-key-only check | PASS |
| English/Hebrew catalog parity | PASS |
| Hebrew RTL behavior | PASS |
| Ruff check and format | PASS |
| Cargo format and check | PASS |
| Migration matrix, empty and 0001–0010 inputs to 0011 | PASS |
| OpenAPI export repeated byte-identically | PASS |

The single Python warning was a third-party Starlette deprecation warning and did not change the result.

## 8. Packaged verification matrix

| Validator | Result |
|---|---|
| Phase 8 packaged validation | Completed; evidence output retained locally |
| Phase 9 packaged validation | Completed; evidence output retained locally |
| Phase 10 product-truth/self-test | `VERIFIED_WORKING` |
| Phase 11M macOS package | `VERIFIED_WORKING` after outer DMG signing correction |
| Phase 12 safe apply | `VERIFIED_WORKING` |
| Phase 13 orchestration | `VERIFIED_WORKING` |
| Phase 14 public-project corpus and package | `VERIFIED_WORKING` |
| Phase 15 product lock | `VERIFIED_WORKING` |
| Native lifecycle | `VERIFIED_WORKING` |
| Updater E2E | `VERIFIED_WORKING` with ephemeral acceptance keys |
| External product network | None observed |

Phase 12 included a successful apply, a forced post-check failure, byte-identical rollback, and stale-source rejection. Native lifecycle included clean launch, single-instance focus, one engine, supervised engine restart, explicit exit, and owned-child cleanup. Updater E2E rejected tampered, wrong-key, incomplete, and downgrade packages while preserving durable data and project identity.

## 9. DMG correction

The first `0.5.0-preview.3` DMG run exposed `dmg_codesign_structure_valid=false`. The outer DMG was then ad-hoc signed and the Phase 11M validator was rerun. The corrected final DMG passed signature structure, read-only mount, exact bundle contents, and clean detach. Only the corrected final hash is listed as the candidate artifact.

## 10. Evidence model

All reports use schema `mellowyak.phase16m.acceptance-evidence.v2` with five independent axes:

- `native_automation_status`
- `human_physical_status`
- `visual_status`
- `functional_status`
- `cleanup_status`

The authoritative per-test matrix is in `PHASE_16M_PHYSICAL_ACCEPTANCE.md` and the machine-readable equivalent is in `PHASE_16M_EVIDENCE_MANIFEST.json`.

## 11. Visual evidence rules

- Files under `images/native` and `images/product` are canonical captures from the installed acceptance work.
- Files under `images/native/notifications` are genuine Notification Center banner captures.
- Files under `images/deterministic` are labeled `DETERMINISTIC_PRODUCT_VIEW — NOT HUMAN PHYSICAL EVIDENCE`.
- The same canonical image may appear in both PDFs.
- Unchanged canonical images reused in this closure retain their original per-image capture commit and app hash. Those values preserve honest capture provenance; the candidate table and top-level manifest identity remain authoritative for the rebuilt final candidate.
- Accessibility automation is evidence for native automation only.
- No screenshot is promoted to a stronger evidence class than its origin supports.

## 12. Privacy remediation

Two original System Settings screenshots exposed unrelated account/sidebar context. They were moved outside the repository and replaced with canonical crops containing only the MellowYak notification controls. The crop operation used local macOS image tooling and did not synthesize UI. The delivery directory was checked to exclude customer source, credentials, databases, browser profiles, support bundles, private full-desktop captures, and normal product data.

## 13. Localization

All GUI copy remains translation-key driven. English is the base catalog; Hebrew contains matching keys and uses RTL. Source checks and React tests passed. The documentation screenshots are English-only by design; localization completeness is verified in code so future catalogs such as Russian can be added without hardcoded component text.

## 14. Human-only boundary

The following remain `HUMAN_PHYSICAL_NOT_RUN` where a real physical boundary is required:

- logout/login with startup enabled and disabled;
- lock/unlock;
- idle and queued sleep/wake;
- complete macOS restart;
- real battery-power transition;
- physical delivered-notification activation for the stale-destination scenario;
- human-observed native banner comparison across Quiet Mode.

These are intentionally not replaced by Accessibility automation or deterministic images.

## 15. Distribution boundary

The app and DMG are ad-hoc signed local technical-preview artifacts. Developer ID signing, notarization, stapling, trusted public distribution, and production updater trust are not configured. Gatekeeper correctly rejected a quarantined ad-hoc build; no bypass is documented.

## 16. Cleanup and restoration

The acceptance configuration is restored to Start at Login off, close-to-tray on, Quiet Mode off, and Activity Mode normal. Acceptance-lab environment variables are unset. Disposable alerts, aliases, test roots, previous installer backup, and isolated acceptance data are removed only after evidence generation. Normal user data is untouched. No app, engine, helper, or mounted DMG is intentionally left after final closure cleanup.

## 17. Git boundary

The implementation commit is local. Documentation and canonical evidence are committed separately after PDF validation. Generated app bundles, DMGs, runtime data, build manifests, Finder Alias artifacts, databases, and private acceptance state are excluded. Nothing is pushed. No `physical-accepted` tag is created.

## 18. Final verdicts

- Product: `INTEL_MAC_TECHNICAL_PREVIEW_ACCEPTED_WITH_LIMITS`.
- Human physical: `HUMAN_PHYSICAL_ACCEPTANCE_PENDING`.
- Distribution: `PUBLIC_MAC_DISTRIBUTION_BLOCKED`.
- Local tag: not created at this closure because the mandatory physical boundary is incomplete.
- Exact next authorized phase: finish the remaining Phase 16M human physical checks against this exact candidate; Phase 17 is not authorized.


## 19. Complete test-axis matrix

Expected and actual details for every row are maintained in `PHASE_16M_PHYSICAL_ACCEPTANCE.md`; the same machine-readable axes and evidence paths are in the v2 manifest.

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

## Expected, actual, evidence, cleanup, and remaining action

| Test ID | Native automation | Human physical | Visual | Functional | Expected | Actual | Evidence | Cleanup | Remaining human action |
|---|---|---|---|---|---|---|---|---|---|
| P15-PHYS-101 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | One translated menu and truthful counters | Native menu inspected; one app/engine | Native tray capture and lifecycle log | PASS | Physically open and confirm |
| P15-PHYS-102 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Existing window focuses safely | Same window/process restored | Installed lifecycle log | PASS | Physically select Open |
| P15-PHYS-103 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NO_VISUAL_EVIDENCE_REQUIRED | PASS | No duplicate app or engine | Second instance exited; one app/engine | Lifecycle validator | PASS | Launch from Finder/Spotlight |
| P15-PHYS-104 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Window hides; monitoring continues | Existing identity remained active | Lifecycle validator | PASS | Physically click red close |
| P15-PHYS-105 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Disabled close-to-tray exits app and engine | Defect reproduced, fixed, rebuilt; installed retest ended at 0 desktop and 0 engine | Accessibility run, Rust regression, process inspection | PASS | Physically repeat with setting off |
| P15-PHYS-106 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | All owned processes exit | Desktop, engine and children exited | Process evidence | PASS | Physically choose tray Quit |
| P15-PHYS-107 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Cmd+Q/menu Quit cleans all children | Shutdown defect fixed; cleanup passed | Process evidence | PASS | Physically use application-menu Quit |
| P15-PHYS-108 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | OS and product permission agree | MellowYak permission enabled | Privacy-safe Settings crop | PASS | None |
| P15-PHYS-109 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | In-app evidence persists; no false claim | Denied state observed and restored | Privacy-safe Settings crop | PASS | None |
| P15-PHYS-110 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | Exactly one redacted native banner | Seven genuine banner scenarios captured | Native notification images | PASS | Trigger and observe a fresh banner |
| P15-PHYS-111 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | Existing app opens safe destination | Alerts destination opened without duplicate | Installed product capture | PASS | Physically click delivered banner |
| P15-PHYS-112 | BLOCKED | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Revalidate and fall back to Alerts | Click-time code/test passes; real stale delivered-banner activation not completed | Source test and build commit | PASS | Perform exact stale delivered-banner click |
| P15-PHYS-113 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Exactly one valid registration | One LaunchAgent registered | LaunchAgent inspection | PASS | Enable physically |
| P15-PHYS-114 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | One app/tray/engine after login | Real login boundary not performed | None | PASS | Logout/login with startup enabled |
| P15-PHYS-115 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Registration removed | LaunchAgent removed and setting restored | LaunchAgent inspection | PASS | Disable physically |
| P15-PHYS-115B | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | No automatic process after login | Real login boundary not performed | None | PASS | Logout/login with startup disabled |
| P15-PHYS-116 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | One coherent process set after unlock | Authentication boundary not performed | None | PASS | Lock 30 seconds and unlock |
| P15-PHYS-117 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | Watcher resumes without duplicate | Physical sleep cycle not performed | None | PASS | Perform real idle sleep/wake |
| P15-PHYS-118 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | Queued work resumes or invalidates safely | Controlled sleep cycle not performed | None | PASS | Sleep/wake with approved queued check |
| P15-PHYS-119 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | Alias resolves to canonical project root | Native chooser resolved disposable Alias | Canonical-resolution capture | PASS | Physically repeat selection |
| P15-PHYS-120 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | Same identity/history; mismatch rejected | Same ID retained; one record; foreign fixture rejected; valid source restored | Installed AX, database evidence, canonical/deterministic images | PASS | Physically repeat both choices |
| P15-PHYS-121 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Exact app installs from read-only DMG | Mounted, verified, installed and detached | Phase 11M validator | PASS | Physically drag app to Applications |
| P15-PHYS-122 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Cold launch produces one app/engine | Installed hashes matched; lifecycle passed | Hash and process evidence | PASS | Physically launch from Finder |
| P15-PHYS-123 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | No duplicate identity or process | Reinstall passed with one app/engine | Package/lifecycle evidence | PASS | Physically reinstall same DMG |
| P15-PHYS-124 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | No processes/startup item/source mutation | App removal preserved isolated data | Package evidence | PASS | Physically move app to Trash |
| P15-PHYS-125 | NATIVE_AUTOMATION_PASS | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | PASS | Retained data opens without corruption | Reinstall passed; one process set | Package evidence | PASS | Physically reinstall and open |
| P15-PHYS-126 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | Documented startup; no duplicate recovery | Real restart not performed | None | PASS | Restart the Intel Mac |
| P15-PHYS-127 | BLOCKED | HUMAN_PHYSICAL_NOT_RUN | VISUAL_PASS | PASS | In-app alert persists; native delivery suppressed, then resumes | Real alert persisted while quiet and state restored; post-quiet native banner was not physically observed | Installed DB/UI evidence plus deterministic Settings view | PASS | Observe before/during/after native banners |
| P15-PHYS-128 | NOT_RUN | HUMAN_PHYSICAL_NOT_RUN | NOT_RUN | NOT_RUN | Optional work defers on real battery state | Host remained on AC; no simulation claimed | Power-state observation | PASS | Disconnect AC and restore it |
