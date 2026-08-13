$ErrorActionPreference = "Stop"

function Show-Provider {
  param(
    [string]$Name,
    [string]$Command,
    [string]$Template,
    [string]$EnvName
  )
  Write-Host "==> $Name"
  Write-Host "template: $Template"
  $resolved = Get-Command $Command -ErrorAction SilentlyContinue
  if ($resolved) {
    Write-Host "status: available"
    Write-Host "path: $($resolved.Source)"
  } else {
    Write-Host "status: not_configured"
    Write-Host "hint: install a compatible CLI or set $EnvName to your real JSON search command."
  }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$xhsTemplate = if ($env:VMF_XHS_SEARCH_COMMAND) { $env:VMF_XHS_SEARCH_COMMAND } else { 'xhs search "{query}" --json --limit {limit}' }
$douyinTemplate = if ($env:VMF_DOUYIN_SEARCH_COMMAND) { $env:VMF_DOUYIN_SEARCH_COMMAND } else { 'dy search "{query}" --json --limit {limit}' }

Show-Provider "Xiaohongshu CLI source" "xhs" $xhsTemplate "VMF_XHS_SEARCH_COMMAND"
Show-Provider "Douyin CLI source" "dy" $douyinTemplate "VMF_DOUYIN_SEARCH_COMMAND"

Write-Host "Stage6 source check completed."
