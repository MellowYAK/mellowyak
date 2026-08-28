[CmdletBinding()]
param(
  [string]$ExpectedCommit = "",
  [string]$BundleRoot = "apps/desktop/src-tauri/target/release/bundle",
  [switch]$LifecycleVerified
)

$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
  $PSNativeCommandUseErrorActionPreference = $true
}
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepositoryRoot
if (-not $IsWindows) { throw "Windows runtime acceptance must run on Windows." }

$Commit = (git rev-parse HEAD).Trim()
if ($ExpectedCommit -and $Commit -ne $ExpectedCommit) { throw "Commit mismatch: expected $ExpectedCommit, found $Commit." }
$TrackedStatus = @(git status --porcelain --untracked-files=no)
if ($LASTEXITCODE -ne 0) { throw "Unable to inspect tracked source status." }
if ($TrackedStatus) {
  throw "Tracked source is dirty before validation: $($TrackedStatus -join '; ')"
}

$Python = Join-Path $RepositoryRoot "engine/.venv/Scripts/python.exe"
if (-not (Test-Path $Python)) { throw "Run scripts/bootstrap-windows.ps1 first." }
& $Python scripts/export_openapi.py
& npm.cmd --prefix apps/desktop run contract:generate
& $Python scripts/check_ui_translation_keys.py
& npm.cmd --prefix apps/desktop run typecheck
cargo check --locked --manifest-path apps/desktop/src-tauri/Cargo.toml

$Sidecar = Get-ChildItem "apps/desktop/src-tauri/binaries/mellowyak-engine-*-pc-windows-msvc.exe" -ErrorAction SilentlyContinue
if (-not $Sidecar) { throw "Windows engine sidecar was not staged." }
$Installer = Get-ChildItem $BundleRoot -Recurse -File | Where-Object { $_.Extension -in @(".exe", ".msi") } | Select-Object -First 1
if (-not $Installer) { throw "No Windows installer artifact was found under $BundleRoot." }

$WebViewKeys = @(
  "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F1E7E2E0-5E7F-4B12-96A2-53B3C75A0C5A}",
  "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F1E7E2E0-5E7F-4B12-96A2-53B3C75A0C5A}",
  "HKCU:\Software\Microsoft\EdgeUpdate\Clients\{F1E7E2E0-5E7F-4B12-96A2-53B3C75A0C5A}"
)
$WebViewAvailable = $WebViewKeys | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $WebViewAvailable) { Write-Warning "WebView2 registry evidence was not found; the NSIS package embeds the Evergreen bootstrapper." }

New-Item -ItemType Directory -Force -Path build-manifest | Out-Null
$ValidationStatus = if ($LifecycleVerified) { "VERIFIED_WORKING" } else { "SOURCE_PACKAGE_VERIFIED" }
& $Python scripts/write_artifact_manifest.py `
  --root $BundleRoot `
  --output build-manifest/windows-x64-artifacts.json `
  --platform windows-x64 `
  --commit $Commit `
  --validation-status $ValidationStatus

Write-Host "Windows acceptance status $ValidationStatus recorded for $Commit. Use -LifecycleVerified only after the documented native lifecycle succeeds."
