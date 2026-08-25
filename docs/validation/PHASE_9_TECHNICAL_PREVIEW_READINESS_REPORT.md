# Phase 9 Technical Preview readiness report

Date: 2026-08-25
Version: `0.2.0-preview.1`
Branch: `product/technical-preview-readiness`
Starting commit: `baba4f493d08ae48722051b245840494577fef40`
Current-platform gate: **VERIFIED_WORKING**

## Acceptance decision

The freshly built Intel macOS application and DMG are accepted as an unsigned local
Technical Preview candidate for operator review. Phase 8 validated-repair safety and
Phase 9 install/readiness behavior passed against the final schema-0009 sidecar using
isolated synthetic data. The application was installed locally only after package
inspection and the prior installation was retained for recovery.

This decision does not authorize a public release. Signing, notarization, Apple
Silicon, Windows, Linux, public updater delivery, and real-project acceptance remain
separate gates.

## Exact source results

- Python: 167 passed; one upstream Starlette deprecation warning; 72.14 seconds.
- React: 19 passed; 20.54 seconds.
- Automated source total: 186 passed.
- TypeScript, Vite, UI translation-key policy, catalog parity/RTL, Ruff check/format,
  Cargo format/check: passed.
- OpenAPI export was byte-deterministic; SHA-256
  `61f59cf602c562d468aaa7840343f18ef02dd61d9bfa3348167c422d31f0efce`.
- Migration matrix: empty and every predecessor 0001–0008 reached
  `0009_technical_preview_readiness` with existing data preserved.

## Phase 8 package compatibility

`PHASE_8_PACKAGED_VALIDATION.json` is `VERIFIED_WORKING`: nine Demo Labs, one
committed/live-verified Apply, one byte-identical post-check rollback, one stale
pre-write block, four byte-identical crash recoveries, one redacted recovery-required
case, and 22 Product Self-Test steps. Authentication, loopback, restart history,
source privacy, no external network, no real projects, and zero orphans passed.

## Phase 9 package acceptance

`PHASE_9_PACKAGED_VALIDATION.json` is `VERIFIED_WORKING`: clean install/schema 0009,
first-run persistence/replay, disconnected project, identity-safe reconnect/relocate,
notification route rejection, private tray/diagnostics, redacted support bundle,
storage `PASS`, signed updater fixtures, Battery Saver safety, source immutability,
installation identity, and Phase 8 upgrade preservation passed.

`PHASE_9_UPDATER_VALIDATION.json` is `VERIFIED_WORKING` for the disposable local
signer: valid signatures accepted; tampered, wrong-key, and interrupted content
rejected; no private key persisted; production configuration unchanged. The actual
production updater remains `IMPLEMENTED_NOT_RUNTIME_VERIFIED`.

## Final package identity

| Component | Size | SHA-256 |
|---|---:|---|
| Application | 721,696 KiB | see binary/tree identities below |
| Desktop | 22,710,536 bytes | `8b93f7fa635fe4d4f566767536d27d843b8794558978dd56528b1093754d6bdd` |
| Engine | 75,262,624 bytes | `30f8d77795cff55f6440f2a251ded70a6f1038135150488b80139412bff63fe7` |
| Browser tree | 623,348 KiB | `e49bacdbdf9904896aa7554cf8b6738be0f88a4aca5972466b14e1b5f9a13bb0` |
| DMG | 389,091,955 bytes | `b75f6bae68c42571346ff7bd8e1e61bdd34e28ad8835921e4ada7ff13c638a66` |

DMG verification/mount/detach, installed-hash equality, single-instance behavior,
close-to-tray, explicit Quit, schema 0009 isolated launch, and zero orphans passed.
Idle CPU after the i18n callback stability fix was 0.1% combined; observed combined
RSS was 226,844 KiB.

## Security and privacy result

No external network, cloud service, model/provider SDK, APC runtime, real source,
user data, production credential, updater private key, or public release was used.
Package scan found no home path, private key, token, database, evidence, or real
project. Support exports rejected secret canaries. Apply remains deliberate,
journaled, snapshot-protected, identity-bound, and freshly verified.

## Limitations

- local application and DMG are unsigned and unnotarized; Gatekeeper rejects them;
- Apple Silicon, Windows, and Linux are workflow-configured, not runtime verified;
- native notification route logic is verified, but a physical OS notification click
  was not automated;
- the production signed update path was not executed;
- no real-project acceptance run occurred;
- the Vite build retains one advisory for a JavaScript chunk over 500 kB;
- the packaged browser tree dominates package size;
- local timing/memory observations are not cross-platform benchmarks.

Detailed evidence and operator guidance are indexed in
`docs/phase-9-delivery/README.md`.
