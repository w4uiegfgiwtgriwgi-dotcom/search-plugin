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
Require-Path "docs/stage5-package-troubleshooting.md"

$BuilderPath = Join-Path $Root "apps/desktop/node_modules/electron-builder"
if (Test-Path $BuilderPath) {
  Write-Host "electron-builder is installed."
} else {
  Write-Host "electron-builder is not installed yet. Run this only after approval:"
  Write-Host "cd E:\搜索插件\apps\desktop"
  Write-Host "npm install --save-dev electron-builder"
}

$DesktopPackage = Get-Content "apps/desktop/package.json" -Raw | ConvertFrom-Json
if (-not $DesktopPackage.scripts.pack) {
  throw "apps/desktop/package.json missing scripts.pack"
}
if (-not $DesktopPackage.scripts.dist) {
  throw "apps/desktop/package.json missing scripts.dist"
}
if (-not $DesktopPackage.build) {
  throw "apps/desktop/package.json missing build config"
}
if ($DesktopPackage.build.files -contains "../*" -or $DesktopPackage.build.files -contains "../../*") {
  throw "desktop build files include parent directory"
}
Write-Host "pack script: $($DesktopPackage.scripts.pack)"
Write-Host "dist script: $($DesktopPackage.scripts.dist)"

$DistPath = Join-Path $Root "apps/desktop/dist/win-unpacked"
if (Test-Path $DistPath) {
  Write-Host "win-unpacked exists."
} else {
  Write-Host "win-unpacked is not generated yet."
}

Write-Host "Stage5 package plan check passed."
