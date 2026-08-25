# Source test report

The final gate executes the full Python and React suites, TypeScript, Vite production build,
translation-only UI checker, English/Hebrew parity and RTL, Ruff check/format, Cargo format/check,
deterministic OpenAPI generation twice and the migration matrix.

Final result:

- Python: 170 passed; one upstream Starlette/httpx deprecation warning.
- React/Vitest: 22 passed; controlled/uncontrolled warning absent.
- TypeScript: passed.
- Vite 6.4.3: passed; 81 modules; no chunk advisory.
- Ruff check: passed; Ruff format: 172 files formatted.
- Translation-only UI: `UI_TRANSLATION_KEYS_ONLY`; English/Hebrew parity and RTL passed.
- Cargo format/check: passed with Rust 1.98.0.
- OpenAPI generated twice with identical SHA-256
  `e8c0b9d83ec83702ad97afadd8aba2c3e935f43db32c80db009ffdf71867a646`.
- Migration matrix: empty and every 0001–0008 source upgraded to
  `0009_technical_preview_readiness` with existing-data canaries preserved.

The React regression test asserts that the warning is absent. No prior test was skipped or weakened.
