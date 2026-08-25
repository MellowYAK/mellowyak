[CmdletBinding()]
param(
  [switch]$InstallMissing,
  [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepositoryRoot

$Required = @("git", "node", "npm", "rustup", "cargo")
$Missing = @($Required | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) })
$HasPython = (Get-Command py -ErrorAction SilentlyContinue) -or (Get-Command python -ErrorAction SilentlyContinue)
if (-not $HasPython) { $Missing += "python" }

if ($Missing.Count -gt 0 -and -not $InstallMissing) {
  if ($NonInteractive) {
    throw "Missing required tools: $($Missing -join ', '). Rerun with -InstallMissing or install them before bootstrap."
  }
  $Answer = Read-Host "Missing tools: $($Missing -join ', '). Install supported packages with winget now? [y/N]"
  if ($Answer -notin @("y", "Y", "yes", "YES")) { throw "Bootstrap cancelled before making changes." }
  $InstallMissing = $true
}

if ($InstallMissing) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "winget is required for -InstallMissing." }
  winget install --id Git.Git --exact --accept-package-agreements --accept-source-agreements
  winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
  winget install --id OpenJS.NodeJS.LTS --exact --accept-package-agreements --accept-source-agreements
  winget install --id Rustlang.Rustup --exact --accept-package-agreements --accept-source-agreements
  winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --accept-package-agreements --accept-source-agreements --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
  throw "Tool installation completed. Open a new PowerShell window, then rerun bootstrap-windows.ps1."
}

if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3.12 -m venv engine/.venv
} else {
  & python -m venv engine/.venv
}

$Python = Join-Path $RepositoryRoot "engine/.venv/Scripts/python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e './engine[dev]'
npm ci --prefix apps/desktop
rustup toolchain install 1.98.0 --profile minimal --component rustfmt --component clippy
& $Python -m playwright install chromium
& $Python scripts/export_openapi.py
npm --prefix apps/desktop run contract:generate

Write-Host "Windows bootstrap complete for $(git rev-parse HEAD)."
