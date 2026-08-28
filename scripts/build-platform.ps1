[CmdletBinding()]
param(
  [ValidateSet("windows-x64")]
  [string]$Platform = "windows-x64",
  [ValidateSet("nsis", "msi")]
  [string]$Bundle = "nsis",
  [switch]$ReleaseUpdater
)

$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
  $PSNativeCommandUseErrorActionPreference = $true
}
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepositoryRoot
$TrackedStatus = git status --porcelain --untracked-files=no
if ($TrackedStatus) { throw "Tracked source is dirty. Commit the shared source before producing a platform artifact." }

$Python = Join-Path $RepositoryRoot "engine/.venv/Scripts/python.exe"
if (-not (Test-Path $Python)) { throw "Run scripts/bootstrap-windows.ps1 first." }

& $Python scripts/export_openapi.py
& npm.cmd --prefix apps/desktop run contract:generate
& $Python scripts/check_ui_translation_keys.py
& npm.cmd --prefix apps/desktop run typecheck
& $Python scripts/stage_browser.py
& $Python scripts/build_engine.py

$TauriArguments = @("--prefix", "apps/desktop", "run", "tauri", "build", "--", "--bundles", $Bundle)
if ($ReleaseUpdater) { $TauriArguments += @("--config", "src-tauri/tauri.release.conf.json") }
& npm.cmd @TauriArguments

$ManifestRoot = Join-Path $RepositoryRoot "build-manifest"
New-Item -ItemType Directory -Force -Path $ManifestRoot | Out-Null
$Commit = (git rev-parse HEAD).Trim()
& $Python scripts/write_artifact_manifest.py `
  --root apps/desktop/src-tauri/target/release/bundle `
  --output "build-manifest/$Platform-artifacts.json" `
  --platform $Platform `
  --commit $Commit `
  --validation-status NOT_RUN

Write-Host "Built $Platform from $Commit. Runtime acceptance remains NOT_RUN."
