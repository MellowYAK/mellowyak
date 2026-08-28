[CmdletBinding()]
param(
  [switch]$InstallMissing,
  [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
if (Test-Path variable:PSNativeCommandUseErrorActionPreference) {
  $PSNativeCommandUseErrorActionPreference = $true
}
$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepositoryRoot

function Get-NvmExecutable {
  $Candidates = @(
    (Join-Path $env:LOCALAPPDATA "nvm/nvm.exe"),
    (Join-Path $env:APPDATA "nvm/nvm.exe"),
    (Join-Path $env:ProgramFiles "nvm/nvm.exe")
  )
  $Command = Get-Command nvm.exe -ErrorAction SilentlyContinue
  if ($Command) { return $Command.Source }
  return $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

function Get-NodeMajor {
  $Node = Get-Command node.exe -ErrorAction SilentlyContinue
  if (-not $Node) { return $null }
  $Version = (& $Node.Source --version).Trim()
  if ($LASTEXITCODE -ne 0 -or $Version -notmatch '^v(?<major>\d+)\.') { return $null }
  return [int]$Matches.major
}

function Get-Python312Launcher {
  if (Get-Command py.exe -ErrorAction SilentlyContinue) {
    try {
      $Version = (& py.exe -3.12 --version 2>&1 | Out-String).Trim()
      if ($LASTEXITCODE -eq 0 -and $Version -match '^Python 3\.12\.') {
        return [pscustomobject]@{ Executable = "py.exe"; Arguments = @("-3.12") }
      }
    } catch {
      # The Microsoft Store launcher can exist even when it cannot resolve an interpreter.
    }
  }
  $Python = Get-Command python.exe -ErrorAction SilentlyContinue
  if (-not $Python) { return $null }
  $Version = (& $Python.Source --version 2>&1 | Out-String).Trim()
  if ($LASTEXITCODE -eq 0 -and $Version -match '^Python 3\.12\.') {
    return [pscustomobject]@{ Executable = $Python.Source; Arguments = @() }
  }
  return $null
}

function Test-VsCppTools {
  $VsWhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio/Installer/vswhere.exe"
  if (-not (Test-Path $VsWhere)) { return $false }
  $Installation = & $VsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
  return ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($Installation | Out-String)))
}

function Add-NvmPathsToProcess {
  $NvmHome = [Environment]::GetEnvironmentVariable("NVM_HOME", "User")
  if (-not $NvmHome) { $NvmHome = [Environment]::GetEnvironmentVariable("NVM_HOME", "Machine") }
  $NvmSymlink = [Environment]::GetEnvironmentVariable("NVM_SYMLINK", "User")
  if (-not $NvmSymlink) { $NvmSymlink = [Environment]::GetEnvironmentVariable("NVM_SYMLINK", "Machine") }
  foreach ($Path in @($NvmHome, $NvmSymlink)) {
    if ($Path -and ($env:Path -split ';') -notcontains $Path) { $env:Path = "$Path;$env:Path" }
  }
}

Add-NvmPathsToProcess
$Nvm = Get-NvmExecutable
$NodeMajor = Get-NodeMajor
$PythonLauncher = Get-Python312Launcher
$Required = @("git", "rustup", "cargo")
$Missing = @($Required | Where-Object { -not (Get-Command $_ -ErrorAction SilentlyContinue) })
if (-not $PythonLauncher) { $Missing += "python-3.12" }
if ($NodeMajor -ne 22) { $Missing += "node-22" }
if (-not (Test-VsCppTools)) { $Missing += "vs-cpp-tools" }

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
  if ($Missing -contains "git") {
    winget install --id Git.Git --exact --accept-package-agreements --accept-source-agreements
  }
  if ($Missing -contains "python-3.12") {
    winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements
  }
  if (($Missing -contains "node-22") -and -not $Nvm) {
    winget install --id CoreyButler.NVMforWindows --exact --accept-package-agreements --accept-source-agreements
    Add-NvmPathsToProcess
    $Nvm = Get-NvmExecutable
  }
  if (-not $Nvm) { throw "NVM for Windows was installed but nvm.exe could not be located. Open a new PowerShell window and rerun bootstrap-windows.ps1 -InstallMissing." }
  if ((Get-NodeMajor) -ne 22) {
    & $Nvm install 22
    if ($LASTEXITCODE -ne 0) { throw "NVM could not install a supported Node.js 22.x release." }
    $Installed22 = Get-ChildItem (Split-Path $Nvm) -Directory -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -match '^v22\.\d+\.\d+$' } |
      Sort-Object { [version]$_.Name.Substring(1) } -Descending |
      Select-Object -First 1
    if (-not $Installed22) { throw "NVM reported success but no installed Node.js 22.x directory was found." }
    & $Nvm use $Installed22.Name.Substring(1)
    Add-NvmPathsToProcess
  }
  if ($Missing -contains "rustup" -or $Missing -contains "cargo") {
    winget install --id Rustlang.Rustup --exact --accept-package-agreements --accept-source-agreements
  }
  if ($Missing -contains "vs-cpp-tools") {
    winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --accept-package-agreements --accept-source-agreements --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
  }
  if ((Get-NodeMajor) -ne 22) { throw "Node.js 22 was installed but is not active. Open an elevated PowerShell once, run 'nvm use 22', then rerun bootstrap-windows.ps1. Do not change the machine execution policy." }
}

$NodeVersion = (& node.exe --version).Trim()
if ((Get-NodeMajor) -ne 22) { throw "MellowYak requires Node.js 22.x; found $NodeVersion. Use NVM for Windows to install and activate Node 22." }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw "npm.cmd was not found beside Node.js $NodeVersion." }

$PythonLauncher = Get-Python312Launcher
if (-not $PythonLauncher) { throw "MellowYak requires Python 3.12.x, but no working Python 3.12 launcher was found." }
$VenvArguments = @($PythonLauncher.Arguments) + @("-m", "venv", "engine/.venv")
& $PythonLauncher.Executable @VenvArguments

$Python = Join-Path $RepositoryRoot "engine/.venv/Scripts/python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -e './engine[dev]'
& npm.cmd ci --prefix apps/desktop
rustup toolchain install 1.98.0 --profile minimal --component rustfmt --component clippy
& $Python -m playwright install chromium
& $Python scripts/export_openapi.py
& npm.cmd --prefix apps/desktop run contract:generate

Write-Host "Windows bootstrap complete for $(git rev-parse HEAD) with Node $NodeVersion."
