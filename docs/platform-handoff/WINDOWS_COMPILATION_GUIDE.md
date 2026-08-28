# MellowYak Windows x64 Compilation Guide

This guide explains how to reproduce a native Windows x64 MellowYak build from the shared source. It contains no machine-specific credentials or acceptance evidence.

## Supported source and toolchain

- Windows 11 x64
- PowerShell 7 recommended
- Git
- Node.js 22.x, selected through NVM for Windows
- npm from the selected Node.js installation
- Python 3.12 x64 with the Windows `py` launcher recommended
- Rust 1.98.0 with `rustfmt` and `clippy`
- Visual Studio 2022 Build Tools with the Desktop development with C++ workload and a current Windows SDK
- Microsoft Edge WebView2 Runtime

The repository pins Node major 22 in `.nvmrc`, Python 3.12 in `.python-version`, and Rust 1.98.0 in `rust-toolchain.toml`. Do not substitute a newer major merely because a package manager labels it LTS.

## Clone and select the source

```powershell
git clone https://github.com/MellowYAK/mellowyak.git
Set-Location mellowyak
git checkout platform/windows-x64
git status --short --branch
```

For a release or acceptance build, check out the exact annotated tag or commit named by the release notes instead of a moving branch.

## Bootstrap

The bootstrap is safe to rerun. It validates the pinned major versions, creates `engine/.venv`, installs locked desktop dependencies, installs the Python engine in editable development mode, installs managed Chromium, and regenerates the OpenAPI TypeScript contract.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
./scripts/bootstrap-windows.ps1 -NonInteractive
```

If prerequisites are missing:

```powershell
./scripts/bootstrap-windows.ps1 -InstallMissing
```

Open a fresh PowerShell window after package installation and rerun the non-interactive command. The bootstrap uses NVM for Windows for Node 22 and invokes `npm.cmd`, so no permanent PowerShell execution-policy change is required.

Verify the active tools:

```powershell
node --version
npm.cmd --version
py -3.12 --version
rustc --version
cargo --version
```

## Native source gates

```powershell
$Python = "engine/.venv/Scripts/python.exe"
& $Python -m pytest engine
& $Python -m ruff check engine scripts
& $Python -m ruff format --check engine scripts
& $Python scripts/export_openapi.py
npm.cmd --prefix apps/desktop run contract:generate
& $Python scripts/check_ui_translation_keys.py
npm.cmd --prefix apps/desktop test
npm.cmd --prefix apps/desktop run typecheck
npm.cmd --prefix apps/desktop run build
cargo fmt --check --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo check --locked --manifest-path apps/desktop/src-tauri/Cargo.toml
cargo clippy --locked --manifest-path apps/desktop/src-tauri/Cargo.toml -- -D warnings
& $Python scripts/validate_migration_matrix.py
git diff --check
```

Generated contracts must remain deterministic. Review `git status` after the gates; unexpected tracked changes are a failure, not generated output to commit blindly.

## Build the Windows package

The supported build wrapper stages managed Chromium, builds the Python engine sidecar, runs contract/localization/type checks, and builds the configured Tauri NSIS package.

```powershell
./scripts/build-platform.ps1 -Platform windows-x64 -Bundle nsis
```

The principal outputs are under:

- `apps/desktop/src-tauri/target/release/`
- `apps/desktop/src-tauri/target/release/bundle/nsis/`
- `build-manifest/windows-x64-artifacts.json`

Do not commit executables, installers, private updater keys, browser profiles, local databases, or acceptance evidence containing user data.

## Installed layout and local test entry points

The per-user NSIS package installs the desktop executable, engine sidecar, bundled browser, and uninstaller under `%LOCALAPPDATA%\MellowYak`. Runtime data is deliberately separate under `%LOCALAPPDATA%\com.mellowyak.desktop\engine`; it must never be written into the installation directory.

```powershell
$InstallRoot = Join-Path $env:LOCALAPPDATA "MellowYak"
$DataRoot = Join-Path $env:LOCALAPPDATA "com.mellowyak.desktop\engine"
$Desktop = Join-Path $InstallRoot "mellowyak-desktop.exe"
$Engine = Join-Path $InstallRoot "mellowyak-engine.exe"
$Uninstaller = Join-Path $InstallRoot "uninstall.exe"

Start-Process -FilePath $Desktop
Get-Process mellowyak-desktop, mellowyak-engine
Get-NetTCPConnection -State Listen |
  Where-Object OwningProcess -In (Get-Process mellowyak-engine).Id
```

The engine port is ephemeral. A healthy installed launch has one loopback listener on `127.0.0.1`, rejects requests without its per-launch bearer token, and remains supervised by the desktop process. Do not record the token in logs or documentation.

## Authenticode signing

Do not describe an unsigned or self-signed package as publicly trusted. A release signer needs a currently valid Windows code-signing certificate with its private key, access to an RFC 3161 timestamp service, and an appropriate key-protection process. With the certificate available in the Windows certificate store, sign the final installer using the Windows SDK x64 `signtool.exe`:

```powershell
$SignTool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
$Thumbprint = "REPLACE_WITH_RELEASE_CERTIFICATE_THUMBPRINT"
$TimestampUrl = "https://REPLACE_WITH_RFC3161_TIMESTAMP_SERVICE"

& $SignTool sign /sha1 $Thumbprint /fd SHA256 /tr $TimestampUrl /td SHA256 `
  "apps\desktop\src-tauri\target\release\bundle\nsis\MellowYak_0.5.0-preview.3_x64-setup.exe"

& $SignTool verify /pa /all /v `
  "apps\desktop\src-tauri\target\release\bundle\nsis\MellowYak_0.5.0-preview.3_x64-setup.exe"
```

Replace the example versioned filename when the product version changes. A public release pipeline must additionally sign the desktop executable and sidecar before they are embedded into NSIS, using the Tauri signing hook or an equivalent split build/bundle pipeline; do not rebuild after signing because that replaces signed artifacts. Keep certificate material and private keys outside the repository.

## Validate the source-bound package

```powershell
$Commit = (git rev-parse HEAD).Trim()
./scripts/validate-windows.ps1 -ExpectedCommit $Commit
```

Do not pass `-LifecycleVerified` until installation, first and subsequent launch, loopback authentication, engine supervision, tray/quit behavior, process cleanup, core protection workflows, Apply/rollback, and uninstall have actually passed against the installed package.

## Distribution boundary

A successful local NSIS build is a technical artifact, not proof of public distribution readiness. Public Windows release also requires trusted Authenticode signing, timestamping, SmartScreen/reputation evidence, protected updater signing keys, and a trusted update channel. Never bypass SmartScreen or use a self-signed certificate to claim public trust.
