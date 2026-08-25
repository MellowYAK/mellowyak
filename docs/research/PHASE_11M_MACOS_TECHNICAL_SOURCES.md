# Phase 11M macOS technical sources

Accessed 2026-08-25. Only public implementation questions were researched; no repository path, source,
project data, credentials or evidence was sent to any external service.

| Area | Primary source | Decision |
|---|---|---|
| Notification activation | [Apple `UNUserNotificationCenterDelegate`](https://developer.apple.com/documentation/usernotifications/unusernotificationcenterdelegate) | Install notification handling before launch completes and route an activation to the already-running window. The physical click remains a manual gate when UI automation cannot operate Notification Center. |
| Hardened runtime | [Apple Hardened Runtime](https://developer.apple.com/documentation/security/hardened-runtime) | Keep entitlements minimal; do not enable JIT, unsigned executable memory or disabled library validation. |
| Notarization | [Apple notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution) | Require Developer ID signing, hardened runtime, secure timestamp, `notarytool` acceptance and stapling for a distributable claim. Ad-hoc signing is structural evidence only. |
| Packaged Python | [PyInstaller operating mode](https://pyinstaller.org/en/stable/operating-mode.html) | Use one-directory on macOS: one-file extracts on every launch and is explicitly slower; the app bundles the private directory as a resource. |
| PyInstaller macOS bundle | [PyInstaller macOS bundles](https://pyinstaller.org/en/stable/usage.html#building-macos-app-bundles) | Do not put a PyInstaller one-file executable inside a second app bundle when a stable one-directory resource is available. |
| Frontend chunking | [Vite build options](https://vite.dev/config/build-options) | Split vendor and large product modules with Rollup chunk boundaries; keep behavior unchanged and measure actual output instead of hiding the warning threshold. |
| Autostart | [Tauri autostart plugin](https://v2.tauri.app/plugin/autostart/) | Retain the LaunchAgent implementation and verify enable, disable and persistence on the disposable acceptance installation. |
| Notifications | [Tauri notification plugin](https://v2.tauri.app/plugin/notification/) | Retain the portable send API; use the underlying macOS notification handle only for desktop activation, because Tauri action registration is mobile-only. |
| Tray | [Tauri system tray](https://v2.tauri.app/learn/system-tray/) | Keep a single translated tray owned by the Tauri process and focus the existing main window. |
| Updater | [Tauri updater](https://v2.tauri.app/plugin/updater/) | Sign every updater artifact; use `.app.tar.gz` plus detached signature on macOS. Allow loopback HTTP only in a disposable test configuration. |
| Hosted macOS runners | [GitHub-hosted runner reference](https://docs.github.com/actions/reference/runners/github-hosted-runners) | Add an Intel macOS workflow and keep Apple Silicon as a separately reported boundary; a configured job is not a remotely executed result. |
