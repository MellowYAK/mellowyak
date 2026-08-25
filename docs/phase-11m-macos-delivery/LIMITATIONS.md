# Phase 11M limitations

- Verified native package scope is Intel macOS x86_64 only.
- Apple Silicon has a configured same-source workflow but no local/runtime evidence.
- The app and DMG are ad-hoc signed, not Developer ID signed or notarized; public distribution is
  blocked.
- Production updater delivery remains unverified and unpublished.
- A physical Notification Center click and physical tray interaction were not automated.
- Real login-session relaunch, sleep/wake, lock/unlock and logout were not triggered.
- Finder alias handling is implemented but not runtime verified; symlink and hard-link safety passed.
- The bundled x86_64 Chrome for Testing runtime still dominates package size.
- The first uncached onedir engine launch can still approach the old onefile time; warm/restart median
  is the measured improvement.
- First Home, first Project Overview and route-specific frontend timing were not separately
  instrumented.
- No real private project was touched. Real-project readiness is an operator guide, not acceptance.
- No Windows or Linux acceptance was performed.
