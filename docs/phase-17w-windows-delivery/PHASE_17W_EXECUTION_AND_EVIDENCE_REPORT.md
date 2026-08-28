# MellowYak Phase 17W Windows x64 Execution and Evidence Report

## Scope and starting checkpoint

Phase 17W extended the accepted shared Intel Mac source into a native Windows x64 technical preview. It did not rewrite product semantics or create a Windows-only fork. The starting repository was `https://github.com/MellowYAK/mellowyak.git`, branch `platform/windows-x64`, commit `a6ed01865418e47b498761172d7e8062beee6ee0`, and annotated source tag `phase-16m-intel-mac-technical-preview-accepted-with-limits-2026-08-28`. The product remained `0.5.0-preview.3` with database head `0011_baseline_lock_and_local_proof`.

The handoff quoted OpenAPI SHA-256 `608ced66dbc65676ab44abae5ed97f070b1ee41af7fc7db127fa35623a66949c3d72f8`. The authoritative tracked file repeatedly produced `576ad581c3f97bd47081a538b257e46920b9de0de5f636b7c70aaca75571ee9f`; the discrepancy is retained rather than rewriting Mac evidence.

At takeover, Python 3.12 and Rust 1.98 were present. NVM for Windows 1.2.2 had been installed but was not visible in the active shell, Node 24 had been removed, and the repository-required Node 22 was unavailable. Visual Studio Code was present but was not treated as the MSVC toolchain. The machine already contained Visual Studio 2022 Build Tools, Windows SDK, WebView2, Git, and authenticated GitHub CLI state.

## Verdict

- Product verdict: `WINDOWS_X64_TECHNICAL_PREVIEW_ACCEPTED_WITH_LIMITS`.
- Installed functional acceptance: `CLOSED`.
- Native lifecycle automation: `CLOSED` for launch, authenticated sidecar, single instance, close-to-tray, reopen, start-at-login toggle/restore, explicit tray Quit, and owned-process cleanup.
- Public distribution: `BLOCKED_UNSIGNED`.
- Human OS-transition checks such as reboot, logout/login, lock/unlock, sleep/wake, and a physical notification click remain `HUMAN_PHYSICAL_NOT_RUN`.

The verdict is limited because no trusted Authenticode certificate/private key is available on the acceptance host. No self-signed artifact is represented as publicly trusted.

## Candidate identity

- Product version: `0.5.0-preview.3`.
- Package build commit: `babfab9ac0aa6e50544f0cd62f7477f70748d0e1`.
- Branch during implementation: `codex/phase17w-windows-x64`, destined to fast-forward `platform/windows-x64`.
- Database head: `0011_baseline_lock_and_local_proof`.
- Installer: `apps/desktop/src-tauri/target/release/bundle/nsis/MellowYak_0.5.0-preview.3_x64-setup.exe`.
- Installer size: `227,786,006` bytes.
- Installer SHA-256: `8739a1566c58ecd32568c0e26b171313d54d55a0abb742596fab2168d40be8cd`.
- Installer Authenticode: `NotSigned`.
- Installed desktop SHA-256: `716ac97c786247fe84d484c93f6c75918750d81dff9ffa11e0165eb4cdc2d3cc`.
- Installed engine SHA-256: `2c2a7b32bfbb77fc7abfc09533c5701f0c38c374c0c765fe93ca541fffac872e`.
- Bundled Chromium launcher SHA-256: `409805a16d6416087e6b2f778df1cf8f7bbb267d6b99f6b5bb0a618eace234f2`.
- Deterministic OpenAPI SHA-256: `576ad581c3f97bd47081a538b257e46920b9de0de5f636b7c70aaca75571ee9f`.

The Phase 16M handoff quoted a different OpenAPI digest. Phase 17W recomputed the tracked file and confirmed byte stability at the value above; history was not rewritten to conceal the discrepancy.

## Host and toolchain

- Windows 11 Pro Insider Preview x64, `10.0.26220`, host `DESKTOP-4EVC0IC`.
- Python `3.12.10`.
- Node `22.23.2`; npm `10.9.8`; NVM for Windows `1.2.2`.
- Rust/Cargo `1.98.0`.
- Visual Studio 2022 Build Tools `17.12.4` with x64/x86 C++ tools and Windows SDK.
- Git `2.55.0.windows.3`.
- Managed Chromium observed by packaged acceptance: `151.0.7922.34`.

Node was repaired by locating the standard NVM for Windows installation, restoring its user environment to normal project shells, installing/selecting compatible Node 22, and changing bootstrap logic to enforce the repository pin instead of allowing the moving `OpenJS.NodeJS.LTS` alias to install Node 24. PowerShell workflows use `npm.cmd` where execution policy would otherwise select the blocked `npm.ps1`; machine-wide execution policy was not weakened. The bootstrap was rerun idempotently after the repair.

## Implementation record

The implementation commits preceding this evidence report are:

- `51add016951c0064235cc35045605567a4061a59` — Windows bootstrap, build, Tauri, engine lifecycle, browser discovery, filesystem, CI, and portability work.
- `93df2ce62462874b0e1f24b1290b116f2f1fb8fd` — Win32 parent supervision and isolation of the installed data root from the NSIS application directory.
- `babfab9ac0aa6e50544f0cd62f7477f70748d0e1` — packaged-validator process-tree cleanup, NTFS release waits, migration cleanup, and Windows Git-observer filtering.

Meaningful changed areas include `.github/workflows`, Windows bootstrap/build/validation scripts, Tauri configuration and Rust lifecycle code, Python engine process/filesystem/browser/storage adapters, packaged acceptance validators, tests, `.gitignore`, and the Windows compilation handoff. Core signal semantics, explicit Apply authorization, Baseline Lock, Yak Receipt, schema 0011, product version, local-first boundary, English/Hebrew architecture, and accepted Mac history were intentionally unchanged.

## Defects found and repaired

1. Windows bootstrap could select a moving Node LTS and did not robustly handle `npm.cmd`, PowerShell native exit codes, or incomplete NVM state. Bootstrap is now pinned, idempotent, and validates the required Windows toolchain.
2. macOS-only Tauri autostart APIs and route assumptions prevented clean Windows compilation. Platform configuration is now conditional.
3. The Tauri parent did not pass the packaged resource directory to the sidecar. Browser/resource discovery is now cross-platform and tested.
4. Windows lacked `tzdata` in the packaged engine. The runtime dependency was added.
5. SQLite/log resources remained open in shutdown and migration tooling. Services now dispose/close handles correctly.
6. `os.kill(parent_pid, 0)` is not a valid Windows liveness probe. The sidecar watchdog now uses Win32 `OpenProcess` and `GetExitCodeProcess`, fixing the installed app's immediate engine exit at `Starting local services`.
7. `%LOCALAPPDATA%\MellowYak` was both the NSIS installation directory and the engine data root. Runtime data now lives at `%LOCALAPPDATA%\com.mellowyak.desktop\engine`.
8. PyInstaller packaged validators terminated only the bootloader and could orphan the Python child. Windows cleanup now terminates the complete process tree and waits for NTFS handle release.
9. Dulwich on Windows surfaced generated `api/__pycache__/` as untracked even when command-line Git reported a clean tree. Generated/cache paths already excluded by product policy no longer invalidate the source identity. A regression test and full Phase 12 packaged browser flow prove the repair.

## Source gates

- Ruff check and format: PASS.
- React/Vitest: `30 passed`.
- TypeScript typecheck: PASS.
- Vite production build: PASS, `92 modules transformed`.
- Cargo format: PASS.
- Cargo check: PASS.
- Cargo clippy with `-D warnings`: PASS.
- Translation-key-only UI check and generated API contract: PASS.
- Migration matrix: empty plus every 0001 through 0010 input upgraded to 0011 with preservation.
- Python: `216 collected`, `210 passed`, `6 skipped`; the skips are expected Windows symlink cases.

Representative exact commands were:

```powershell
engine\.venv\Scripts\python.exe -m ruff check engine scripts
engine\.venv\Scripts\python.exe -m ruff format --check engine scripts
engine\.venv\Scripts\python.exe -m pytest
npm.cmd --prefix apps\desktop test -- --run
npm.cmd --prefix apps\desktop run typecheck
npm.cmd --prefix apps\desktop run build
cargo fmt --manifest-path apps\desktop\src-tauri\Cargo.toml --check
cargo check --locked --manifest-path apps\desktop\src-tauri\Cargo.toml
cargo clippy --locked --manifest-path apps\desktop\src-tauri\Cargo.toml -- -D warnings
engine\.venv\Scripts\python.exe scripts\check_ui_translation_keys.py
engine\.venv\Scripts\python.exe scripts\test_migration_matrix.py
```

The Python run initially encountered only fixture/cache ACL problems when temporary roots were placed inside Git-controlled or sandbox-managed directories. The final elevated native run with a normal Windows temporary directory collected 216 tests and passed 210 with six intentional Windows symlink skips. This is recorded as environment repair, not as a hidden retry of a product failure.

## Build, install, migration, and package identity

The release path used the repository abstraction and NSIS only:

```powershell
.\scripts\bootstrap-windows.ps1 -NonInteractive
.\scripts\build-platform.ps1 -Platform windows-x64 -Bundle nsis
```

The package was built from clean product commit `babfab9ac0aa6e50544f0cd62f7477f70748d0e1`, then installed per-user. Documentation commits are intentionally later and do not pretend that the already-hashed installer came from their self-referential commit. No MSI is claimed. Empty databases and each historical input from migrations 0001 through 0010 upgraded to 0011 with preservation; no schema or product-version bump was needed.

The install directory is `%LOCALAPPDATA%\MellowYak`; persistent engine state is `%LOCALAPPDATA%\com.mellowyak.desktop\engine`. Uninstall/reinstall proved those roots no longer collide. The exact package artifact is not committed to Git.

## Installed native acceptance

The final NSIS package was silently installed per-user. The installed directory contains only `browser`, `mellowyak-desktop.exe`, `mellowyak-engine.exe`, and `uninstall.exe`. Runtime directories are absent from the install root and present under the separate data root.

After launch, the application rendered live Home content instead of remaining at `Starting local services`. At 70 seconds uptime there was one desktop process, the expected PyInstaller bootloader/child pair, one established UI connection, and one listener at `127.0.0.1:62678`. No-auth `/health` returned 401 and an intentionally wrong bearer token returned 401. The installed Phase 15 validator then used its known ephemeral acceptance token and returned authenticated `VERIFIED_WORKING` health, self-test, privacy, schema, version, lineage, and Yak Receipt results.

Lifecycle results:

- Second launch exited and retained one desktop/two engine processes: PASS.
- Window close hid the window while the tray and engine remained alive: PASS.
- Relaunch reopened the existing instance without duplication: PASS.
- Start-at-login created `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\MellowYak` with the installed executable, then disabling it removed the entry: PASS and restored off.
- Native tray menu exposed private counts and `Quit MellowYak`: PASS.
- Invoking tray Quit left zero desktop processes, zero engine processes, and zero owned listeners: PASS.
- Uninstall/reinstall preserved the separate data root while restoring a clean installation directory: PASS.

## Installed packaged workflows

- Phase 8: `VERIFIED_WORKING`; auth, loopback-only, nine Demo Labs, 22 self-test steps, candidate validation, Apply, rollback, four crash recoveries, stale-source block, no network, no orphan.
- Phase 9: `VERIFIED_WORKING`; clean install, 0008 to 0011 upgrade preservation, diagnostics/support redaction, storage integrity, wrong reconnect rejection, updater fixture rejection/acceptance boundaries.
- Phase 10: `VERIFIED_WORKING`; Product Truth, candidate/apply/rollback, 22-step self-test, zero pending recovery, no outbound product network.
- Phase 12M: `VERIFIED_WORKING`; real bundled Chromium capture, runtime profiles, Known Good, controlled regression, actual evidence, repair workspace, valid/invalid candidates, Apply, post-check rollback, byte-identical restoration, stale-source block, no orphan, no external network.
- Phase 13M: `VERIFIED_WORKING`; policy revisions and allowed-hours/budgets persist across restart, malformed policy rejected, self-test PASS.
- Phase 15M: `VERIFIED_WORKING`; authentication required, schema/version/local-only/self-test/Yak Receipt/product-lock routes and clean exit PASS.

The packaged validators ran against the installed engine executable, with disposable project/database roots under the user's Windows temporary directory rather than inside the repository. Phase 12M took 52.5 seconds and used the bundled Chromium, not an emulated browser. Each validator verified clean exit/no orphan where its contract applies. Product runtime observation showed no external connection; dependency download, GitHub, and operating-system traffic were not misclassified as product traffic.

## Security and distribution boundary

Windows Defender was enabled and recorded zero detections for the exact final installer path. The installed engine exposed only an authenticated loopback listener. Acceptance projects and databases were disposable; no real project was modified and no source was uploaded.

The Windows SDK includes `signtool.exe`, but both Current User and Local Machine certificate stores contained zero currently valid Code Signing certificates with accessible private keys. Consequently the installer and application binaries remain unsigned. Public release requires trusted Authenticode signing and RFC 3161 timestamping, signing embedded binaries before NSIS packaging, signature-chain verification, SmartScreen/reputation evidence, protected updater signing keys, and a trusted update channel.

The requested `mellowyak.com` and `www.mellowyak.com` names returned no DNS result from the acceptance host on 2026-08-28. No website content was invented or treated as verified.

`signtool.exe` is available at `C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe`. Both `Cert:\CurrentUser\My` and `Cert:\LocalMachine\My` contained zero valid Code Signing certificates with accessible private keys. Therefore no properly trusted signature can be produced on this host. The Windows compilation guide records the required embedded-binary and outer-installer signing order and RFC 3161 verification commands. A self-signed substitute was deliberately not created.

## Native and human gate matrix

| Gate | Evidence class | Result | Reason |
| --- | --- | --- | --- |
| Bootstrap/toolchain | native source environment | PASS | pinned Node/Python/Rust/MSVC/SDK/WebView2 validated |
| Source gates | source test | PASS | lint, tests, type/build, Rust, migrations, i18n/API contract |
| NSIS build/install | package artifact + installed app | PASS | real per-user installer and clean install root |
| Startup/auth/local bind | installed native app | PASS | live Home, authenticated ephemeral 127.0.0.1 engine |
| Product workflows | packaged deterministic | PASS | Phases 8/9/10/12M/13M/15M verified |
| Tray/startup/process cleanup | native automation | PASS | single instance, hide/reopen, Run key restore, explicit Quit |
| Defender | distribution boundary | PASS | enabled; zero detections for exact installer path |
| Authenticode/SmartScreen | distribution boundary | BLOCKED | trusted signing identity/private key unavailable |
| Reboot, login, lock, sleep, physical notification click | human/OS transition | NOT RUN | not silently inferred from automation |

## Evidence inventory and privacy

The screenshot delta contains one `NEW_SCREEN`, three `RECAPTURED_CHANGED`, zero `REUSED_UNCHANGED`, one `RETIRED`, and zero `BLOCKED_NO_CAPTURE` images. The retired image is the superseded startup failure retained for diagnostic lineage. Canonical crops expose no source code, bearer tokens, credentials, account pages, or unrelated desktop data. Phase 16M images remain referenced by provenance and were not duplicated.

Both PDFs were rendered back to PNG with Poppler and every page was visually inspected. The machine-readable page counts, byte sizes, SHA-256 values, and visual/privacy result are in `PHASE_17W_PDF_QA.json`.

## Repository and release finalization boundary

The evidence commit, normal branch push, CI run status, and annotated tag are finalized only after the tracked documentation passes `git diff --check` and integrity checks. The accepted tag name is `phase-17w-windows-x64-technical-preview-accepted-with-limits-2026-08-28`; it must not be pushed if branch CI exposes a product failure. Because a commit cannot truthfully contain its own final object ID or prove its later network push, final Git object IDs and remote CI status are reported in the operator handoff alongside this immutable report.

## Canonical Windows evidence

### Clean installed Home

![Final installed MellowYak Home after authenticated startup](images/native/01-installed-home-clean.png)

### Installed Settings

![Final installed Settings screen](images/native/02-installed-settings.png)

### Startup and tray controls

![Close-to-tray enabled and start-at-login restored off](images/native/03-installed-startup-tray.png)

### Native tray menu

![Native Windows tray menu with private counts and Quit](images/native/04-native-tray-menu.png)

### Superseded failure retained as blocked evidence

![Initial installed startup failure before watchdog and data-root repairs](images/blocked/00-superseded-startup-failure.png)

The blocked image is historical diagnostic evidence only. It does not represent the accepted candidate.

## Final decision

The Windows x64 installed application is accepted for local technical-preview use with explicit distribution limits. The functional and native automation gates described above are closed. Public distribution and the unperformed human OS-transition gates remain open; they are not silently converted to passes.
