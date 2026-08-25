# Phase 10 limitations

- The verified package is Intel macOS x86_64 only.
- macOS Apple Silicon, Windows x64 and Linux x64 are configured from the same source but not runtime
  accepted in this phase.
- The local app and DMG are unsigned and unnotarized; Gatekeeper rejects them.
- No public release, push, production updater delivery or code-signing credential was used.
- Regression Detail is unit/integration verified with project isolation; its disposable packaged
  scenario does not fabricate a persistent real regression record.
- Native notification route policy is verified, but a physical operating-system notification click
  was not automated.
- The deterministic tray image is a test-only preview, not a native tray screenshot.
- No real private project acceptance was run; Demo Lab and temporary repositories are the evidence.
- `No confirmed issue` and `Healthy` are bounded by available evidence and are not zero-regression
  guarantees.
- Vite retains a >500 kB chunk advisory; the packaged browser runtime dominates artifact size.
- React's synthetic First Run test emits one non-failing controlled/uncontrolled warning.
- Cold-start, idle CPU and memory numbers are local observations, not cross-platform benchmarks.
- Production signing/notarization, public updater, accounts, cloud/team operation, model connectors,
  automatic repair, automatic Apply, Git push and deployment are not implemented or accepted here.
