$ErrorActionPreference = "Stop"

function Run-Step {
  param(
    [string]$Name,
    [scriptblock]$Command
  )
  Write-Host "==> $Name"
  & $Command
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed with exit code $LASTEXITCODE"
  }
}

function Require-Path {
  param([string]$Path)
  if (-not (Test-Path $Path)) {
    throw "missing required path: $Path"
  }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Run-Step "Stage4 checks" {
  powershell -ExecutionPolicy Bypass -File scripts/stage4-check.ps1
}

Run-Step "Required project files" {
  Require-Path "apps/desktop/package.json"
  Require-Path "apps/desktop/main.cjs"
  Require-Path "apps/desktop/api-process.cjs"
  Require-Path "apps/local-api/requirements.lock.txt"
  Require-Path "docs/license-review.md"
  Require-Path ".gitignore"
}

Run-Step "FFmpeg available" {
  ffmpeg -version | Select-Object -First 1
}

Run-Step "Python available" {
  .\.venv\Scripts\python.exe --version
}

Run-Step "Desktop dependencies present" {
  Require-Path "apps/desktop/node_modules/electron"
}

Run-Step "Runtime environment check" {
  powershell -ExecutionPolicy Bypass -File scripts/stage5-runtime-check.ps1
}

Write-Host "Stage5 preflight passed."
