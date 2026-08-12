$ErrorActionPreference = "Stop"

function Require-Path {
  param([string]$Path)
  if (-not (Test-Path $Path)) {
    throw "missing required path: $Path"
  }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "==> Package plan prerequisites"
Require-Path "apps/desktop/package.json"
Require-Path "apps/desktop/main.cjs"
Require-Path "apps/desktop/api-process.cjs"
Require-Path "apps/desktop/src/index.html"
Require-Path "docs/stage5-windows-package-plan.md"

$BuilderPath = Join-Path $Root "apps/desktop/node_modules/electron-builder"
if (Test-Path $BuilderPath) {
  Write-Host "electron-builder is installed."
} else {
  Write-Host "electron-builder is not installed yet. Run this only after approval:"
  Write-Host "cd E:\搜索插件\apps\desktop"
  Write-Host "npm install --save-dev electron-builder"
}

Write-Host "Stage5 package plan check passed."
