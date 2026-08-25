# Phase 8 research summary

Research was bounded to official primary documentation and did not include source, evidence, private
paths, or user data. The exact URLs, access dates, versions, and decisions are recorded in
[`../research/PHASE_8_TECHNICAL_SOURCES.md`](../research/PHASE_8_TECHNICAL_SOURCES.md).

Decisions informed by the research:

- Python `os.replace`, file flush/`fsync`, and directory sync are used as platform-aware building
  blocks, with explicit limits instead of a universal atomicity claim.
- Path canonicalization, root confinement, symlink rejection, case-fold collision checks, and exact
  hashes precede writes.
- Windows locked-file behavior is treated as a blocking error; MellowYak does not force-close an
  unrelated application.
- Durable journal state is written before source mutation and after every ordered operation.
- Tauri capability separation keeps analysis/validation distinct from the explicit Apply boundary.
- Child processes use direct executable/argv invocation, bounded output, tracked ownership, and
  cleanup; no shell is invoked.
- Playwright is used only for deterministic local delivery screenshots and PDF generation.
