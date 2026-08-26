# MellowYak Phase 14M Master Report

## 1. Executive result

Phase 14M is implemented as the Intel macOS real-world compatibility release candidate for MellowYak `0.4.0-preview.1`. The verified outcome is `VERIFIED_WITH_MANUAL_MACOS_BOUNDARIES_PENDING` and the release state is `INTEL_MAC_RELEASE_CANDIDATE_READY`. This is an installation-specific result, not a claim of universal framework support.

The work closed the previously unverified Phase 13M implementation, created its verified local source tag, branched Phase 14M from that verified source, hardened compatibility against four pinned public repositories plus a Git-less copy, rebuilt the Intel package, and atomically installed the final application in `/Applications/MellowYak.app`.

## 2. Scope and product law

MellowYak remains a local, non-AI product. It does not read prompts, IDE conversations, or provider tokens; it does not upload source or evidence; and it does not generate or apply repairs automatically. Impact chooses bounded checks but never claims causation. Unknown, unsupported, runtime-unavailable, flaky, and non-comparable outcomes remain explicit.

No APC source, private customer project, production credential, updater production channel, or active MellowYak development checkout was used as an acceptance project. Public repositories were used only as disposable local clones and were not committed.

## 3. Source provenance and Git state

- Repository: `https://github.com/MellowYAK/mellowyak.git`
- Phase 13M implementation commit: `93ff5546e03163adb1f4d98ae5cc44dc781cbb6a`
- Phase 13M verified closure commit: `7e750c1619cbb404fb900d3ce8fe165ae4314d50`
- Phase 13M verified local tag: `phase-13m-passive-sentinel-verified-2026-08-26`
- Phase 14M branch: `product/real-world-public-project-compatibility`
- Phase 14M version: `0.4.0-preview.1`
- Database head: `0010_passive_sentinel_orchestration`
- Final Phase 14M commit and tag are created locally at delivery time and are reported by `git rev-parse HEAD` and `git rev-parse phase-14m-real-world-compatibility-verified-2026-08-26^{}`.

Unrelated Finder Alias files under the older Phase 5 delivery directory were preserved and excluded from the commit. No push or GitHub Release was performed.

## 4. Phase 13M closure

Phase 13M was not accepted from its implementation commit alone. Daily global/project runtime budgets, persisted consumption, local-day reset, running-job reservation, restart/crash accounting, allowed-hour and overnight-window policy, timezone/daylight-saving boundaries, bounded audited Run Now override, scheduler fairness, stale-job rejection, alert deduplication, runtime-unavailable copy, and package integration were completed and verified.

The Phase 13M closure used product version `0.3.0-preview.2`. Its complete source result was 198 Python tests and 28 Vitest tests passing, with TypeScript, Vite, Rust, Ruff, translation, deterministic OpenAPI, portability, migration, and packaged gates green. Phase 13M package hashes were:

- application executable: `1ec356382f353cfb94b2c2c2662b7c29ec74cb402735f6fa1776769733711074`
- packaged engine: `71fcfd4d33d3fb3856a3663c07df747b1e4b549e57ed77de8df89e952c74525e`
- DMG: `89aa14c0e85847ac807fb4b47e6879868e08566c443a9f0c8712f2f2f76970d3`

## 5. Reference host

- macOS `26.5.2` build `25F84`, Intel `x86_64`
- Node `v26.7.0`
- npm `11.19.0`
- Python `3.11.5`
- rustc `1.98.0 (88d9e12ae 2026-08-18)`
- cargo `1.98.0 (797e8a9bc 2026-08-05)`

This phase makes no native acceptance claim for Windows, Linux, Apple Silicon, or a different toolchain. Shared domain code remains platform-neutral and process execution remains executable plus argv with a confined working directory, never a shell command string.

## 6. Primary-source research

Runtime and repository rules were checked against the upstream repositories and their official manifests, Python packaging metadata conventions, npm deterministic installation behavior, Git worktree semantics, Apple filesystem-event behavior, and Tauri packaging conventions. Research informed detection and limits; it was not treated as proof of compatibility.

## 7. Public-project corpus

| Alias | Upstream | Pinned commit | Tracked files | License |
|---|---|---:|---:|---|
| Datasette | `https://github.com/simonw/datasette.git` | `0337fba234bf574629d56be631468ea060495fa0` | 328 | Apache-2.0 |
| Excalidraw | `https://github.com/excalidraw/excalidraw.git` | `e1bb9ff8f8931e783c11d104abb8967ac6605c9a` | 1,271 | MIT |
| Vite | `https://github.com/vitejs/vite.git` | `493cc7d43269860fe499a30980d729b0adc93d2c` | 2,806 | MIT |
| Tauri | `https://github.com/tauri-apps/tauri.git` | `5e2856e3209d4ab16d21a1f828ff94b46a35a0b6` | 1,124 | MIT/Apache-2.0 |

The corpus lived under an ephemeral `/tmp` boundary with separate pristine and working copies. Datasette also had a recoverable Git-less copy. Pristine commits and bytes were rechecked after mutations. Supabase, Airbyte, and Saleor were evaluated and rejected because their size/runtime shape would weaken bounded, deterministic Phase 14M acceptance.

## 8. Compatibility model

Compatibility is typed through explicit states including runtime approval required, passive-monitoring ready, observe-only, unsupported, runtime unavailable, and supported-with-limits. The API and project overview expose detected structures, runtime owners, package managers, safe command profiles, prerequisites, limitations, known facts, unknowns, and a safe next action.

Python and Node adapters now detect nested package roots and workspace ownership. Node detection covers package/workspace/workspace-package owners and is capped at 128 runtime candidates. Python is capped at 64 candidates. An explicit MellowYak runtime manifest takes precedence over inferred adapters.

## 9. Real compatibility results

| Project | Detected structures | Runtime candidates | Initial state | Approved state |
|---|---|---:|---|---|
| Datasette | Git, Python, Node, polyglot | 2 | `NEEDS_RUNTIME_APPROVAL` | `READY_FOR_PASSIVE_MONITORING` |
| Datasette Git-less | Git-less, Python, Node, polyglot | 2 | `NEEDS_RUNTIME_APPROVAL` | `READY_FOR_PASSIVE_MONITORING` |
| Excalidraw | Git, nested packages, Node | 12 | `NEEDS_RUNTIME_APPROVAL` | `READY_FOR_PASSIVE_MONITORING` |
| Tauri | Git, Cargo, Node workspace, Node | 22 | `NEEDS_RUNTIME_APPROVAL` | `READY_FOR_PASSIVE_MONITORING` |
| Vite | Git, Node workspace, Node | 128 bounded | `NEEDS_RUNTIME_APPROVAL` | `READY_FOR_PASSIVE_MONITORING` |

Large repositories are fully inventoried for registration while UI samples, relationship fan-out, and automatic check selection remain bounded. Unsupported or omitted behavior remains unknown, not passed.

## 10. File classification and source safety

The scanner classifies source, tests, dependency manifests, dependency locks, generated output, build output, caches, ignored paths, sensitive metadata, and unsupported paths. Sensitive files are represented by safe metadata only and their contents do not enter screenshots or evidence. Symlink directories are not traversed beyond the project boundary. Generated, cache, dependency, and build churn is excluded or bounded according to policy.

The implementation fixed leading-dot path normalization and preserved correct treatment of `.env`, `.npmrc`, and similar sensitive names. Candidate and validation workspaces can perform a full safe scan, while incremental Episode fan-out remains limited.

## 11. Watcher, snapshots, and rescans

Filesystem bursts settle into Episodes, then incremental snapshots, impact selection, a persistent queue, and bounded approved checks. Watcher gaps, overflow-style conditions, restart, and stale source identity trigger typed rescans instead of silently continuing stale work. Duplicate bursts and incidents are deduplicated.

Observation and snapshotting remain active outside allowed runtime hours or after optional runtime budgets are exhausted. Only optional execution is deferred; recovery and source observation are not disabled.

## 12. Real behaviors

Nine real, local behaviors passed on the pinned corpus: two browser, one HTTP/API, one process-health, two test, and three CLI behaviors. Every command used executable plus argv, confined cwd, bounded timeout, redacted arguments, and loopback-only service access.

- Datasette home browser: PASS
- Datasette table browser: PASS
- Datasette JSON API: PASS
- Datasette exact version CLI: PASS
- Datasette process health: PASS
- Excalidraw JavaScript syntax test: PASS
- Vite JavaScript syntax CLI: PASS
- Tauri IPC JavaScript syntax test: PASS
- Git-less Datasette CLI: PASS

All passed on their first attempt. The final behavior distribution was Browser 2, CLI 3, HTTP 1, Process 1, Test 2.

## 13. Harmless change and impact behavior

Harmless, recoverable changes were observed in all five working copies. No confirmed regression was created. Settling and impact stayed bounded, selected checks carried evidence-bound reasons, and omitted checks remained unknown. Measured end-to-end harmless Episode durations were approximately 15.6–63.7 seconds depending on repository size; impact ratios stayed between `0.006141` and `0.013298`.

Lockfile and large-fan-out cases do not become regressions merely because files changed. Daily budget exhaustion reports `DAILY_RUNTIME_BUDGET_EXHAUSTED`; outside-hours deferral reports `OUTSIDE_ALLOWED_HOURS`; explicit Run Now remains bounded and user initiated.

## 14. Regression, flakiness, and unavailable runtime

A controlled disposable Datasette mutation produced a comparable failure, a second comparable attempt, and exactly one deduplicated `CONFIRMED` incident. A fail-then-pass scenario remained `FLAKY`. A missing runtime remained `RUNTIME_UNAVAILABLE`/observe-only rather than becoming a product regression. Non-comparable and omitted checks never became confirmed evidence.

## 15. Repair Workspace, Apply, and rollback

The confirmed incident created an isolated Repair Workspace and retained the original failed behavior as a safe validation check. An invalid candidate failed; a valid candidate passed. Source identity was rechecked immediately before Apply. Apply committed only after live verification. A controlled post-apply failure exercised rollback, which restored byte-identical source and left the unrelated sentinel unchanged. The candidate remained retained and recoverable; pending recovery count returned to zero.

No automatic repair generation or automatic Apply was introduced.

## 16. Security and privacy

Command arguments and environment canaries were checked for evidence leakage. Sensitive HTTP headers were rejected. Sensitive-file values were not read. Product-originated outbound network was absent; public cloning and research were external setup activities, not product traffic. No public source, virtual environment, database, browser profile, snapshot, repair workspace, candidate source, recovery bundle, evidence bytes, user data, credential, or local absolute path is committed.

SQLite concurrency was hardened with WAL, a 30-second busy timeout, and a matching SQLAlchemy connection timeout to prevent false lock failures during realistic concurrent observation.

## 17. Localization and RTL

GUI copy is translation-key-only. English is the source catalog and Hebrew has key parity with full RTL direction. Phase 14M compatibility, safety, runtime, scheduler, and repair copy was added to both catalogs. Screenshot documentation is intentionally English-only. The catalog shape keeps future languages additive without changing UI code.

## 18. Performance and 30-minute soak

The bounded soak completed with `VERIFIED_WORKING` after `1,800.063` seconds. It recorded 310 samples, 12 bounded runtime executions, six harmless filesystem bursts, one restart, zero duplicate incidents, zero Chromium processes after shutdown, and no owned child processes. Source bytes were identical at the end.

- average CPU: `37.286%`
- CPU time: `671.177` seconds
- RSS: `99,151,872` initial, `238,141,440` peak, `138,948,608` growth
- database: `10,637,312` initial, `33,730,560` final, `23,093,248` growth
- object store: 31-object / `11,351,871`-byte delta

These figures describe this Intel host and this isolated corpus; they are not cross-platform benchmarks.

## 19. Automated gates and exact results

- Python source suite: `208 passed, 1 warning in 115.62s`
- React/Vitest: `28 passed in 21.34s`
- TypeScript and Vite production build: PASS
- Ruff format/check: PASS
- Cargo format/check: PASS
- UI translation rule: `UI_TRANSLATION_KEYS_ONLY`
- English/Hebrew catalog parity and Hebrew RTL: PASS
- Migration matrix: empty database and every `0001`–`0009` input migrated to `0010`, data preserved
- deterministic OpenAPI SHA-256: `88472c9e7df73caef53baf1ca7797721efc440c90cd938e56df8021e56eaf5fb`
- public-project production-path validator: `VERIFIED_WORKING`
- final packaged Phase 14M validator: `VERIFIED_WORKING`, all 31 checks true
- Phase 8/9/10/11M/12M/13M package validators: PASS
- updater E2E: all 22 checks true, zero engine orphans

An accidental repository-root pytest invocation discovered tests inside packaged PyInstaller internals; it is not a product source gate. The correct scoped source gate is `pytest engine/tests`, whose exact result is recorded above.

Per the operator's final instruction, no additional validation cycle was run after the final documentation/install step; remaining physical interaction is assigned to the manual operator.

## 20. Packaging and updater

Fresh Intel artifacts were built from the Phase 14M source:

- app: `apps/desktop/src-tauri/target/release/bundle/macos/MellowYak.app`
- DMG: `apps/desktop/src-tauri/target/release/bundle/dmg/MellowYak_0.4.0-preview.1_x64.dmg`
- desktop executable SHA-256: `56076ed7db21ac795c96cb788379daf6f9b119049b48899e6c4a276b813dfdd2`
- packaged engine SHA-256: `53ba9ff8ca64fe2d435ff363b2628be80fdd145645d663788545ad614f6f41d7`
- DMG SHA-256: `81941595972cea8b58fa432a3fb3bd998fd0a87847fefef89701663fdf6b60c7`

The updater fixture upgraded `0.3.0-preview.2` to `0.4.0-preview.1`. Its local fixture artifact was `395,336,349` bytes with SHA-256 `1dcbd8d55930d904027177cb94c8286b7c7f6cfae7c27f1f5dfc79df308f`. No production channel was published or changed.

## 21. Installation

The final app was installed atomically to `/Applications/MellowYak.app` from the fresh bundle. The prior installed version was preserved recoverably as `/Applications/MellowYak-previous-20260826-215250-5b82ce.app`. Installed executable and engine hashes match the fresh bundle:

- installed desktop: `56076ed7db21ac795c96cb788379daf6f9b119049b48899e6c4a276b813dfdd2`
- installed engine: `53ba9ff8ca64fe2d435ff363b2628be80fdd145645d663788545ad614f6f41d7`

## 22. Signing and distribution boundary

The bundle and DMG are ad-hoc signed and structurally valid for local Intel acceptance. No Developer ID Application certificate, notarization credential, or production updater signing credential was available. Gatekeeper/notarized public distribution is therefore not claimed. Status: `IMPLEMENTED_NOT_RUNTIME_VERIFIED` for Developer-ID/notarization distribution only.

## 23. Manual macOS boundaries

The following remain `NOT_RUN` unless a human operator genuinely performs them: physical tray/menu-bar click behavior, Notification Center interaction, System Settings permission flows, logout/login, sleep/wake, lock/unlock, Finder Alias interaction, and public Gatekeeper/notarization behavior. These do not invalidate source/package acceptance, but they prevent claiming complete physical macOS UX acceptance.

## 24. Screenshots and user manual

The companion [Phase 14M User Manual](PHASE_14M_USER_MANUAL.md) documents all 41 deterministic English acceptance screens. Each section embeds its image and explains the backing entity, prior/current state, selected and omitted checks, known facts, unknowns, source-modification boundary, safe next action, and what the operator should expect. The same content is supplied as [PDF](PHASE_14M_USER_MANUAL.pdf). All images are in [`images/`](images/).

The images contain no private source, secret, evidence payload, absolute local path, or copied public-repository source. Hebrew screenshots are intentionally omitted to avoid duplicating documentation; Hebrew catalog parity and RTL are still enforced.

## 25. Limitations and Phase 15 readiness

MellowYak does not claim full support for every framework, script, symlink shape, external service, platform, or omitted behavior. Runtime execution still requires explicit approval. Runtime candidates and relationship fan-out are intentionally capped. The validated package is Intel macOS only, and Developer ID/notarization remains pending.

Within those boundaries, Phase 14M is ready to serve as the immutable source for later Windows x64, Linux x64, and macOS arm64 work. Those platforms must receive their own native acceptance; this report must not be reused as proof for them.

## 26. Delivery inventory

The delivery intentionally contains only the two human-readable English sources requested by the operator, their image directory, and the generated PDF form of the manual:

1. `PHASE_14M_MASTER_REPORT.md` — this consolidated implementation and acceptance report.
2. `PHASE_14M_USER_MANUAL.md` — screen-by-screen operator manual.
3. `PHASE_14M_USER_MANUAL.pdf` — generated portable rendering of the manual.
4. `images/` — 41 English deterministic screenshots referenced by both manual formats.

Raw validation JSON, logs, public clones, runtime data, and package artifacts are intentionally outside this Git delivery.
