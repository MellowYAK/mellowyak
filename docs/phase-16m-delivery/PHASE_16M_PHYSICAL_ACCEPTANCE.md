# MellowYak Phase 16M Physical Acceptance

## Evidence contract

`PASS` requires a genuine operator action, explicit confirmation, timestamped physical screenshot, process/log evidence, and cleanup. Accessibility scripting, deterministic screenshots, source inspection, and automated lifecycle checks are supporting evidence only.

Final candidate: version `0.5.0-preview.2`, build `e0110dc53f83c8a0dfb3135de0bbf44c68f6bffb`, desktop `b16b911f39787b57fc051b467fe503cbd9273f2c3031e79051187b1037dfdc2f`.

The native notification lab produced seven supporting banner images under `images/native-notifications/`. They prove rendering and translated content only; P15-PHYS-108 through P15-PHYS-112 remain `NOT_RUN` until the required physical operator actions are completed.

| Test | Preconditions / operator action | Expected | Actual | Status | Evidence | Cleanup / restoration |
|---|---|---|---|---|---|---|
| P15-PHYS-101 | Installed app running; physically click menu-bar icon | One translated native menu; truthful status; one desktop/engine | Awaiting operator | NOT_RUN | None | Close menu |
| P15-PHYS-102 | Hide/close window; choose Open from tray | Existing window focuses and route/state is safe | Awaiting operator | NOT_RUN | None | Keep app running |
| P15-PHYS-103 | Launch again from Finder/Spotlight | Second process exits; no duplicate engine/watcher | Awaiting operator | NOT_RUN | None | Keep one instance |
| P15-PHYS-104 | Close-to-tray on; click red close | Window hides; engine and monitoring remain | Awaiting operator | NOT_RUN | None | Restore window |
| P15-PHYS-105 | Disable close-to-tray; click red close | Behavior matches documented policy | Awaiting operator | NOT_RUN | None | Restore original enabled value |
| P15-PHYS-106 | Choose Quit from tray | Desktop, engine, and owned children exit | Awaiting operator | NOT_RUN | None | Relaunch for next test |
| P15-PHYS-107 | Use application-menu Quit | Same complete cleanup | Awaiting operator | NOT_RUN | None | Relaunch |
| P15-PHYS-108 | Open System Settings Notifications for MellowYak | OS and product permission state agree | Awaiting operator | NOT_RUN | None | Record original permission |
| P15-PHYS-109 | Deny notifications; generate eligible synthetic alert | In-app alert persists; no false delivery claim/duplicate | Awaiting operator | NOT_RUN | None | Preserve evidence; restore later |
| P15-PHYS-110 | Allow notifications; generate a new alert | Exactly one redacted native notification | Awaiting operator | NOT_RUN | None | Clear test notification |
| P15-PHYS-111 | Physically click delivered notification | Existing app focuses exact safe destination | Awaiting operator | NOT_RUN | None | Return to neutral route |
| P15-PHYS-112 | Click notification after destination is made stale | Safe same-project fallback; no crash/duplicate | Awaiting operator | NOT_RUN | None | Remove synthetic destination |
| P15-PHYS-113 | Enable Start at Login in MellowYak | One correct OS registration | Awaiting operator | NOT_RUN | None | Kept for 114 |
| P15-PHYS-114 | Logout/login with Start at Login enabled | One app/tray/engine; policy restored | Awaiting operator | NOT_RUN | None | Resume from checkpoint |
| P15-PHYS-115 | Disable Start at Login | Registration removed without stale duplicate | Awaiting operator | NOT_RUN | None | Kept disabled for 115B |
| P15-PHYS-115B | Logout/login with Start at Login disabled | No automatic app or orphan engine | Awaiting operator | NOT_RUN | None | Relaunch manually |
| P15-PHYS-116 | Lock 30 seconds, then unlock | One engine; coherent tray/window; no duplicate work | Awaiting operator | NOT_RUN | None | None |
| P15-PHYS-117 | Sleep/wake while idle | Watcher recovers; no duplicates/stale classification | Awaiting operator | NOT_RUN | None | None |
| P15-PHYS-118 | Sleep/wake with one approved idempotent queued check | Resume or invalidate safely after source recheck | Awaiting operator | NOT_RUN | None | Remove queued fixture |
| P15-PHYS-119 | Create real Finder Alias and select through native flow | Canonical disposable root; no duplicate/escape/write | Awaiting operator | NOT_RUN | None | Retain for 120 |
| P15-PHYS-120 | Relocate fixture and reconnect via Alias | Identity-safe reconnect; mismatch rejected | Awaiting operator | NOT_RUN | None | Restore fixture layout |
| P15-PHYS-121 | Mount final DMG and physically drag app to Applications | Exact app installs; prior version recoverable | Awaiting operator | NOT_RUN | None | Clean detach |
| P15-PHYS-122 | Launch from Applications using Finder | Cold launch; handshake; one app/engine/tray | Awaiting operator | NOT_RUN | None | Keep app running |
| P15-PHYS-123 | Physically reinstall same version from DMG | No duplicate identity/startup/watcher/tray/project | Awaiting operator | NOT_RUN | None | Clean detach |
| P15-PHYS-124 | After Quit and Start at Login off, move app to Trash | No process/startup item/source mutation; policy truthful | Awaiting operator | NOT_RUN | None | Retain data per policy |
| P15-PHYS-125 | Reinstall final DMG | Retained data behavior matches; one engine; no corruption | Awaiting operator | NOT_RUN | None | Keep installed |
| P15-PHYS-126 | Restart macOS with checkpoint | Documented startup; no duplicate recovery/notification | Awaiting operator | NOT_RUN | None | Resume from checkpoint |
| P15-PHYS-127 | Enable Quiet Mode; generate eligible alert | In-app evidence remains; native delivery suppressed | Awaiting operator | NOT_RUN | None | Restore Quiet Mode off |
| P15-PHYS-128 | Enable power-saving state and queue noncritical browser work | Observe deferral, then current-only resume | Awaiting operator | NOT_RUN | None | Restore original AC/normal mode |

## Original-state restoration

Start at Login, close-to-tray, Quiet Mode, Activity Mode, notification permission, launch environment, application installation, and retained application data must be restored to the locally recorded originals after the matrix unless the operator explicitly chooses otherwise.
