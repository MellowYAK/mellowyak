# Phase 9 verification evidence

## Source gates

| Gate | Exact result |
|---|---|
| Python | 167 passed; one upstream Starlette deprecation warning; 72.14 s |
| React | 19 passed in one file; 20.54 s |
| Total automated source tests | 186 passed |
| TypeScript | passed |
| Vite production build | passed; JS 501.99 kB (135.49 kB gzip), CSS 38.76 kB (8.71 kB gzip); one >500 kB chunk advisory |
| UI translation policy | `UI_TRANSLATION_KEYS_ONLY` |
| English/Hebrew parity and RTL | passed |
| Ruff check | passed |
| Ruff format | 151 files formatted and clean |
| Cargo format | passed |
| Cargo check | passed |
| OpenAPI determinism | two exports both SHA-256 `61f59cf602c562d468aaa7840343f18ef02dd61d9bfa3348167c422d31f0efce` |
| Migration matrix | empty and 0001–0008 inputs all upgraded to 0009 with data preserved |

## Packaged Phase 8 compatibility gate

`PHASE_8_PACKAGED_VALIDATION.json` reports `VERIFIED_WORKING` against the final
0009-compatible sidecar:

- 9 Demo Lab runs;
- 1 committed Apply and live verification;
- 1 post-Apply failure with byte-identical rollback;
- 1 stale-source block before write;
- 4 crash recovery points with byte-identical restoration;
- 1 recovery-required case that stopped writes and produced a redacted bundle;
- 22 Product Self-Test steps;
- bearer authentication, loopback-only operation, clean restart history, and zero
  orphan processes verified;
- no real project, external network, source upload, or production service used.

Exact Phase 8 package timings:

| Flow | Seconds |
|---|---:|
| Cold startup | 29.050024 |
| Restart startup | 18.602042 |
| Candidate generation and validation | 0.018914 |
| Apply and post verification | 0.093085 |
| Failed post verification and rollback | 0.109035 |
| Product Self-Test | 0.023430 |

## Packaged Phase 9 gate

`PHASE_9_PACKAGED_VALIDATION.json` reports `VERIFIED_WORKING`:

- clean install reached schema `0009_technical_preview_readiness`;
- clean-flow duration after engine-start helper: 19.028404 seconds;
- first-run persistence and replay passed;
- disconnected project visibility passed;
- wrong reconnect was rejected;
- relocate preserved history and did not move source;
- forged/stale notification routes were rejected;
- tray and diagnostics exposed no private path/source content;
- support export redacted secret canaries;
- storage integrity returned `PASS`;
- valid updater fixture was accepted; invalid signature, tampered, and interrupted
  fixtures were rejected; no-update behavior remained stable;
- Battery Saver preserved the safety core;
- source stayed byte-identical and installation identity persisted;
- Phase 8 -> Phase 9 upgrade preserved existing data and identity and skipped first
  run for the existing installation;
- no real projects or external network were used.

## Native application lifecycle

- Fresh application and DMG built from version `0.2.0-preview.1`.
- DMG checksum verified, mounted read-only, contained the application and correct
  `/Applications` link, matched final executable hashes, and detached cleanly.
- Second instance exited immediately while the existing application remained active.
- Closing the red window control left no on-screen layer-0 window but retained the
  supervised desktop/engine process.
- Explicit Quit terminated both; orphan count was zero.
- Final application was installed under `/Applications/MellowYak.app` after retaining
  a timestamped recovery copy, launched once against isolated data, reached schema
  0009, and quit cleanly.

## Idle behavior

The pre-fix packaged process used about 48% combined CPU because translated alert
polling was recreated after every render. Memoized translation callbacks and a
regression test reduced the observed packaged idle result to 0.1% combined CPU.
Observed combined resident memory was 226,844 KiB across the desktop and engine
processes. These are local observations, not cross-platform benchmarks.
