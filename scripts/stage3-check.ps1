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

Run-Step "Node unit tests" {
  npm test
}

Run-Step "Local API tests" {
  npm run test:api
}

Run-Step "Browser extension syntax" {
  Push-Location "apps/browser-extension"
  try {
    node --check "src/popup.js"
  } finally {
    Pop-Location
  }
}

Run-Step "Electron smoke" {
  Push-Location "apps/desktop"
  try {
    npm run smoke
  } finally {
    Pop-Location
  }
}

Write-Host "Stage3 checks passed."
