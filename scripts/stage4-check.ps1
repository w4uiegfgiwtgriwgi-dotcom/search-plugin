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

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Run-Step "Stage3 baseline checks" {
  powershell -ExecutionPolicy Bypass -File scripts/stage3-check.ps1
}

Run-Step "Desktop renderer syntax" {
  node --check "apps/desktop/src/renderer.js"
}

Run-Step "Stage4 report exists" {
  if (-not (Test-Path "docs/stage4-wechat-channel-semi-auto-report.md")) {
    throw "missing docs/stage4-wechat-channel-semi-auto-report.md"
  }
}

Run-Step "Stage4 manual acceptance exists" {
  if (-not (Test-Path "docs/stage4-manual-acceptance.md")) {
    throw "missing docs/stage4-manual-acceptance.md"
  }
}

Write-Host "Stage4 checks passed."
