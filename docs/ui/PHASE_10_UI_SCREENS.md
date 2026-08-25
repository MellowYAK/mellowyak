# Phase 10 UI screen map

The canonical visual inventory is `docs/phase-10-delivery/PHASE_10_SCREEN_GUIDE.md` with 36 PNG files,
HTML and PDF variants. It covers:

- First Run welcome, unselected/selected path, background settings and completion;
- Home empty/attention states;
- Project Overview healthy/limited states;
- Activity, Episode, checks and behaviors;
- friendly/technical regression detail;
- Repair Workspace and candidate validation;
- Apply confirmation/progress/success and safe rollback;
- disconnected source, identity preview and mismatch;
- Diagnostics, Product Self-Test, support bundle, updater and activity modes;
- test-only tray preview;
- Hebrew RTL Home, Overview, Regression and Diagnostics.

All captures use synthetic deterministic state. The real native tray is implemented in Rust/Tauri and
is not represented by the test-only web preview as if it were an OS capture.
