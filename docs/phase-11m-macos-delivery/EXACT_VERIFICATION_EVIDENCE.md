# Exact verification evidence

The source baseline was commit `8620786c3e4598cd9564ba19a38e84b8e1aaa96d` at annotated tag
`phase-10-product-truth-verified-2026-08-25`. Work is on
`product/macos-native-hardening`. Product version remains `0.2.0-preview.1`; schema remains
`0009_technical_preview_readiness`.

Baseline: Python 170 passed; React/Vitest 22 passed with one warning; TypeScript, Vite, Ruff,
translation/RTL, Cargo, OpenAPI determinism and the empty/0001–0008 migration matrix passed.
OpenAPI SHA-256 was
`e8c0b9d83ec83702ad97afadd8aba2c3e935f43db32c80db009ffdf71867a646`.

Final exact test output and artifact identities are recorded in `SOURCE_TEST_REPORT.md`,
`PACKAGE_INVENTORY.md` and the adjacent JSON reports. Physical tray click, physical Notification
Center click, real login relaunch, sleep/wake, Apple Silicon runtime, Developer ID, notarization,
public updater delivery and private-project acceptance are not represented as passed.
