# MellowYak Phase 16M Physical Acceptance

## Evidence model

Schema: `mellowyak.phase16m.acceptance-evidence.v2`. Each axis is independent. Accessibility automation and deterministic screenshots are never human physical evidence.

Candidate: `0.5.0-preview.3`; build commit `a24d9f7e252c71f4d389493988ffd38075783807`; DMG SHA-256 `ada29bfe1c9887256f057279ee7e201cad0ea6db3a379bb980a6466ffe3ce7dd`.

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

## Honest boundary

Human physical acceptance remains pending wherever the human axis says `HUMAN_PHYSICAL_NOT_RUN`. P15-PHYS-112 and P15-PHYS-127 are `BLOCKED` on the native-automation axis because their full native banner activation/observation sequence was not completed, even though their source/functional behavior passed.

## Restoration

Start at Login is disabled, close-to-tray is enabled, Quiet Mode is off, Activity Mode is normal, all acceptance launch variables are unset, the installed app is closed, owned child processes are zero, disposable acceptance data was moved to Trash, and normal user data was untouched.
