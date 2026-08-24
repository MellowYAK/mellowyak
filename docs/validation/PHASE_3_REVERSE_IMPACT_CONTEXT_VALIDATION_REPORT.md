# Phase 3 Reverse Impact and Context Receipt validation

## Startup asset matte correction

The eight startup frames are extracted deterministically from the canonical source sheet. The source contains a baked light checkerboard and gray shadow rather than real transparency, so extraction now removes the connected neutral matte and one contaminated neutral edge pixel. All frames retain a shared 320×363 canvas and were reviewed against the application's dark navy background to prevent visible cutout halos.

- Date: 2026-08-24
- Scope: Phase 3 static impact/context foundations plus required macOS startup and English/Hebrew UI corrections; user-directed mascot and updater foundations were added afterward without changing the Phase 3 intelligence claims
- Overall local status: VERIFIED_WORKING
- Remote CI status: NOT_RUN_FOR_LOCAL_PHASE3_COMMIT

## Starting Git safety

- Exact base: `38a9058990f0e4eff4e53d85019775cdde8f7931`
- Base state: clean
- Origin: `https://github.com/MellowYAK/mellowyak.git`
- Annotated local safety tag: `phase-2-project-git-impact-verified-2026-08-24`
- Working branch: `product/reverse-impact-context-foundation`
- APC: inspected read-only; no APC file, database, credential or deployment was modified
- Push/release: not performed

## Architecture and persisted model

Status: VERIFIED_WORKING

Migration `0003_reverse_impact_context` adds only Phase 3 entities: stable project changes, analysis/input/result/path records, Context Receipts/items, and behavior candidates/links. Tests exercise empty creation and upgrades from both `0001_local_core` and `0002_project_git_impact`, preserving an existing project row.

`reverse-impact-v1` begins at exact changed FILE/TEST nodes. A clean Change is keyed by committed `base HEAD → current HEAD`; a dirty Change is keyed by `HEAD + deterministic worktree fingerprint`. Analysis records the base/head, fingerprint, scan revision, algorithm and policy. Relevant Git or scan changes make old analyses stale rather than silently current.

## Traversal rules and bounds

Status: VERIFIED_WORKING

Default bounds are depth 4, 250 results, 3 paths per result, heuristic depth 1, 1,500 ms, 50 unknown expansions and 48,000 explanation bytes. Hard clamps prevent caller expansion beyond depth 8, 2,000 results, 10 paths, heuristic depth 2, 10 seconds, 250 unknown expansions and 256,000 explanation bytes.

Parsed and heuristic edges produce different classes/ranking. Unknown and stale facts are visible terminal results. Truncation reasons are deterministic. A 1,001-node/1,000-edge fixture stopped at 250 results and completed below the two-second test ceiling.

Fixture example:

```text
src/formatTime.ts (changed)
← IMPORTS / STATIC_HEURISTIC — src/RescheduleModal.tsx
← IMPORTS / STATIC_HEURISTIC — tests/reschedule.spec.ts
```

The integration fixture yields the changed file, a one-hop related component and a two-hop test when the explicit heuristic-depth policy permits it. A dynamic unresolved reference yields `UNKNOWN_BOUNDARY`; a relation from an older scan yields `STALE_RELATION` and traversal stops there.

## Context Receipt

Status: VERIFIED_WORKING

Schema `mellowyak.context_receipt.v1` is deterministic for the same project, Change, analysis, optional task intent and budgets. Budgets are 20 files, 20 symbols, 12 relationship paths, zero snippets, zero source bytes and 65,536 JSON bytes. Every selected item includes provenance, relevance class, selection reasons and a human-readable reason. Unknown, stale, sensitive, missing and over-budget items are reported under unknown/excluded context.

Verified example properties:

```json
{
  "schema": "mellowyak.context_receipt.v1",
  "source_uploaded": false,
  "size_metrics": { "selected_source_bytes": 0 },
  "constraints": {
    "max_files": 20,
    "max_source_bytes": 0,
    "source_content_included": false,
    "sensitive_content_eligible": false
  }
}
```

A 28-consumer fixture proves the file budget and records `file_budget` exclusions.

## Behavior candidates

Status: VERIFIED_WORKING

Impacted, non-stale test names may create candidates. Verified transitions are `CANDIDATE → DISMISSED`, `DISMISSED → CANDIDATE`, and `CANDIDATE → PROMOTED_STUB`. API/UI always say not protected and verification not configured. No Protected Behavior, evidence or PASS/FAIL state is created.

## UI and localization

Status: VERIFIED_WORKING

The desktop contains project navigation, Change Detail, Changed Files, Related Entities, Impact Paths, Unknown/Stale Boundaries, Context Receipt generation/copy/details, Behavior Candidate controls, and an incoming/outgoing Impact Explorer.

All static product copy in React is referenced through typed translation keys. Complete English and Hebrew dictionaries are compile-time checked. Hebrew sets both the document and application to `lang="he" dir="rtl"`; path/JSON technical blocks remain explicitly LTR. The interface starts from the host locale and can switch languages locally without a network call or browser tracking storage.

The no-hardcoded-copy contract is the first README rule and is enforced in CI by `scripts/check_ui_translation_keys.py`, including accessible image descriptions. The supplied transparent mascot sheet was preserved byte-for-byte (SHA-256 `0474b4ce3c2e0ba305c6f3187cda689941ba842ce44d3af16837ab1ec2732b8e`), split into 16 reviewed transparent poses with clean outer padding, documented in JSON/Markdown manifests, and used only on sparse support states.

The final UI review under `docs/ui-review/phase-3-2026-08-24/` contains 24 full-resolution screenshots, English and Hebrew RTL coverage, real-startup and narrow-window states, the icon and mascot masters, per-screen actions/design notes, a 25-page PDF, and a Phase 3/APC extraction summary. All visible project data is synthetic.

The user-supplied 1536×1024 startup sheet is preserved in `assets/mascot/loading/sheet/` (SHA-256 `e0851800f5b51764381ec42fb0e63191b6b5b2e81b920dfafd49d76d0fe685c8`). The delivered file was RGB with a baked checkerboard rather than true transparency. The reproducible extractor removes only edge-connected bright neutral background, applies one union crop to all eight row-major 384×512 cells, and exports eight matching 321×369 RGBA canvases. The UI preloads them, pauses when hidden, stops at frame 8, and uses frame 2 for reduced motion.

Startup now has one authoritative frontend state driven by real operations: engine bootstrap and `/health`; `/installation` plus `/storage/paths`; `/readiness` plus `/settings/privacy`; `/projects`; then a synchronous final consistency handoff after every request has resolved. Ready is impossible until the snapshot and the populated or intentionally empty project array are both stored. Timers are limited to animation, a minimum 800 ms anti-flash interval, a 450 ms genuine-ready hold, a 180 ms fade, and the slow-work explanation. Failure preserves the completed stages, marks the failing stage, exposes translated details and retries the same pipeline.

After the original Phase 3 scope was implemented, the user explicitly requested a signed-release/in-app-update foundation. The desktop now checks the public GitHub Releases `latest.json`, offers a translated install/restart action, and embeds only the updater public key. This newer instruction overrides the original Phase 3 auto-update exclusion. The remote update path is IMPLEMENTED_NOT_RUNTIME_VERIFIED until a higher signed Release exists; no release was published.

## macOS crash report and correction

The supplied crash report is retained as a BROKEN failed attempt: the old desktop aborted in `tao::app_delegate::did_finish_launching` about 21.8 seconds after launch. This aligns with the former blocking 20-second sidecar handshake timeout and is documented as an evidence-based inference, not symbolicated proof of the error string.

The correction moves sidecar handshake processing out of blocking Tauri setup. The window starts immediately, `engine_bootstrap` reports `ENGINE_STARTING`, and the frontend retries for a bounded 60 seconds. A spawn/handshake failure is displayed rather than returned from the AppKit setup callback. A built GUI process remained alive past 30 seconds, beyond the former crash window. Automated UI coverage simulates `ENGINE_STARTING` followed by success.

## Privacy and security evidence

Status: VERIFIED_WORKING

- unique secret fixture absent from receipt JSON, clipboard payload, SQLite and the complete data root;
- sensitive `.env` excluded;
- Phase 3 tables have no source/snippet content columns;
- absolute source roots absent from receipts;
- API cross-project access rejected;
- startup/scan/analysis/receipt test runs with socket connection attempts denied;
- packaged process socket inspection finds loopback only;
- no embeddings, model/provider SDK, connector, analytics or browser storage;
- the optional desktop update check is the only configured non-loopback endpoint; it targets public GitHub Release metadata and sends no project/source/evidence data;
- bearer auth, origin restriction and loopback binding from Phases 1–2 remain tested.

## Tests and exact local results

Status: VERIFIED_WORKING

- Python: 40 passed (`pytest -q`), including Phase 1 and Phase 2 regression coverage
- React: 10 passed (`vitest run`), including early-ready prevention, project-hydration gating, failed-step retry, reduced motion, signed updates and translated mascot accessibility copy
- TypeScript/Vite: passed (`tsc --noEmit`, production build)
- Ruff: passed for engine and Phase 3 package validator; full configured CI lint passes after retaining explicit bootstrap/import suppressions
- Rust: `cargo fmt --check` and `cargo check` passed
- OpenAPI: generated twice identically; SHA-256 `151006c67caadc5bf534afec29ed71fb8d6da0e8b473a908888cbce683527995`
- Migration: empty, Phase 1 and Phase 2 upgrade paths passed
- UI: authoritative startup ordering/retry/reduced-motion, English live-engine values, Hebrew RTL, native picker, Change Detail/receipt/candidates and Impact Explorer passed
- Starlette emitted one upstream `TestClient` deprecation warning; no test failed because of it

## Packaging evidence

Status: VERIFIED_WORKING on this Intel macOS host for the local installed app and Phase 3 packaged-engine flow

- current built `.app`: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
- current installed `.app`: `/Applications/MellowYak.app`
- current desktop executable SHA-256: `ec72758f487aaf3a8884e0e7b7e5a81f92490db31e48bda8fbdce98bf194f5d2`
- current bundled engine SHA-256: `c96605fd67bfac207b476b088c2081502e5acf45cc6139f2fcf98e9e53e422e3`
- prior verified DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.1.0_x64.dmg`
- prior verified DMG SHA-256: `d30af40486ae7079727ac6bed400389ca1e72463aa691e730e204e358a4857c7`

The read-only DMG was checksum-verified, mounted and inspected after the Phase 3/mascot build. It contains both desktop and packaged-engine executables. The later updater addition was installed by the user-requested local app-only path, so the listed DMG is intentionally not claimed as the current updater build and must not be published. Future DMG/NSIS/AppImage/DEB builds belong to the signed GitHub Release workflow.

The packaged fixture flow created a Git repository, connected and scanned it, detected a dirty exact Change, generated impact and a zero-source Context Receipt, shut down, restarted with the same SQLite data, reloaded both records, confirmed loopback-only sockets, and shut down cleanly. It passed again against `/Applications/MellowYak.app/Contents/MacOS/mellowyak-engine`. The installed desktop and engine hashes exactly match the final local `.app`; the GUI remained alive for more than two minutes, beyond the previous crash window. The final installer found no prior target at replacement time, so it correctly did not claim or create a previous-version backup during this run.

## Files modified

Implementation areas: engine database/API/Git/scanner/project/impact modules; migration `0003`; desktop API/App/styles/i18n/mascots/startup/updater; Rust sidecar and updater lifecycle; engine and React tests; generated OpenAPI; deterministic mascot/startup extractors; packaged fixture and local macOS installer; macOS/Windows/Linux CI and signed-release configuration; README, privacy, security, index, contracts, ADR, migration, release and validation documentation. Generated packages, databases, caches, PyInstaller work output, Rust targets and node modules remain ignored and uncommitted.

## Limitations and Phase 4 prerequisites

- Windows and Linux: IMPLEMENTED_NOT_RUNTIME_VERIFIED for this local commit; remote CI has not run because nothing was pushed.
- Apple Silicon and platform code signing/notarization: UNKNOWN/not performed. The updater public/private key pair exists, but remote signed update delivery cannot be verified before the first configured Release.
- Static adapter coverage is partial and cannot prove a complete blast radius.
- Heuristic relationships remain visibly heuristic; unknown remains unknown.
- No runtime instrumentation, Browser Runtime, screenshots, traces or automatic test execution.
- No Protected Behaviors, Last Known Good, verification, regression decision, Completion Gate, repair automation, connectors, cloud, accounts or token-savings claims.

Phase 4 must introduce explicit behavior definitions and evidence lineage before any protection or regression language is permitted. It must not reinterpret Phase 3 candidates as verified history.

## Commit and CI state

The final commit is the single local commit containing this report; its hash is intentionally reported after commit because a commit cannot contain its own content hash. No push, release or remote workflow run was performed. A local updater key pair was generated outside the repository; only the public verification key is committed.
