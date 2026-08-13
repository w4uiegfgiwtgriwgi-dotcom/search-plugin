$ErrorActionPreference = "Stop"

param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("xiaohongshu", "douyin")]
  [string]$Platform,
  [string]$Browser = "chrome",
  [switch]$QrCode
)

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$SearchCliHome = if ($env:VMF_SEARCH_CLI_HOME) { $env:VMF_SEARCH_CLI_HOME } else { Join-Path $env:LOCALAPPDATA "VideoMaterialFinder\search-cli" }
New-Item -ItemType Directory -Force $SearchCliHome | Out-Null

$env:VMF_SEARCH_CLI_HOME = $SearchCliHome
$env:HOME = $SearchCliHome
$env:USERPROFILE = $SearchCliHome
$env:APPDATA = Join-Path $SearchCliHome "AppData\Roaming"
$env:LOCALAPPDATA = Join-Path $SearchCliHome "AppData\Local"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
New-Item -ItemType Directory -Force $env:APPDATA | Out-Null
New-Item -ItemType Directory -Force $env:LOCALAPPDATA | Out-Null

function Resolve-SourceCommand {
  param([string]$Command)
  $resolved = Get-Command $Command -ErrorAction SilentlyContinue
  if ($resolved) { return $resolved.Source }
  foreach ($suffix in @(".exe", ".cmd", ".bat", "")) {
    $candidate = Join-Path $Root ".venv\Scripts\$Command$suffix"
    if (Test-Path $candidate) { return (Resolve-Path $candidate).Path }
  }
  throw "未找到 $Command 命令，请先安装对应候选源 CLI。"
}

if ($Platform -eq "xiaohongshu") {
  $xhs = Resolve-SourceCommand "xhs"
  if ($QrCode) {
    & $xhs login --qrcode
  } else {
    & $xhs login --cookie-source $Browser --json
  }
  $cookiePath = Join-Path $SearchCliHome ".xiaohongshu-cli\cookies.json"
} else {
  $dy = Resolve-SourceCommand "dy"
  & $dy login --browser
  $cookiePath = Join-Path $SearchCliHome ".dy\cookies\default.json"
}

Write-Host "search CLI data home: $SearchCliHome"
if (Test-Path $cookiePath) {
  Write-Host "login: ready"
  Write-Host "cookie: $cookiePath"
} else {
  Write-Host "login: not_detected"
  Write-Host "cookie expected: $cookiePath"
}
