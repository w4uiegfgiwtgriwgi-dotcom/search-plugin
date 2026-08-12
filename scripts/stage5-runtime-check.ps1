$ErrorActionPreference = "Stop"

function Check-Command {
  param(
    [string]$Name,
    [string]$Command,
    [string[]]$Arguments
  )
  Write-Host "==> $Name"
  $output = & $Command @Arguments 2>&1
  if ($LASTEXITCODE -ne 0) {
    throw "$Name failed: $output"
  }
  $output | Select-Object -First 1
}

function Require-Path {
  param([string]$Path)
  if (-not (Test-Path $Path)) {
    throw "missing required path: $Path"
  }
  Write-Host "ok: $Path"
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Check-Command "Node available" "node" @("--version")
Check-Command "npm available" "npm" @("--version")
Check-Command "Python venv available" ".\.venv\Scripts\python.exe" @("--version")
Check-Command "FFmpeg available" "ffmpeg" @("-version")

Write-Host "==> Local API port"
$connection = Test-NetConnection -ComputerName 127.0.0.1 -Port 17860 -WarningAction SilentlyContinue
if ($connection.TcpTestSucceeded) {
  Write-Host "port 17860 is already open; desktop will reuse an existing local API if compatible."
} else {
  Write-Host "port 17860 is free; desktop can start the bundled local API process."
}

Write-Host "==> Required writable/runtime directories"
Require-Path ".local-data"
Require-Path "apps/desktop/node_modules"
Require-Path "apps/local-api"

Write-Host "==> Git ignore safety"
$gitignore = Get-Content ".gitignore" -Raw
foreach ($pattern in @(".local-data/", ".venv/", "node_modules/", "*.sqlite")) {
  if ($gitignore -notmatch [regex]::Escape($pattern)) {
    throw ".gitignore missing $pattern"
  }
  Write-Host "ignored: $pattern"
}

Write-Host "Stage5 runtime check passed."
