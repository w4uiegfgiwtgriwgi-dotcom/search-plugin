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
  $venvResolved = $null
  foreach ($suffix in @(".exe", ".cmd", ".bat", "")) {
    $candidate = Join-Path $Root ".venv\Scripts\$Command$suffix"
    if (Test-Path $candidate) {
      $venvResolved = Resolve-Path $candidate
      break
    }
  }
  if ($resolved) {
    Write-Host "status: available"
    Write-Host "path: $($resolved.Source)"
  } elseif ($venvResolved) {
    Write-Host "status: available"
    Write-Host "path: $venvResolved"
  } else {
    Write-Host "status: not_configured"
    Write-Host "hint: install a compatible CLI into .venv or set $EnvName to your real JSON search command."
  }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
$SearchCliHome = if ($env:VMF_SEARCH_CLI_HOME) { $env:VMF_SEARCH_CLI_HOME } else { Join-Path $env:LOCALAPPDATA "VideoMaterialFinder\search-cli" }

$xhsTemplate = if ($env:VMF_XHS_SEARCH_COMMAND) { $env:VMF_XHS_SEARCH_COMMAND } else { 'xhs search "{query}" --type video --json' }
$douyinTemplate = if ($env:VMF_DOUYIN_SEARCH_COMMAND) { $env:VMF_DOUYIN_SEARCH_COMMAND } else { 'dy search "{query}" --type video --count {limit} --json-output' }

Show-Provider "Xiaohongshu CLI source" "xhs" $xhsTemplate "VMF_XHS_SEARCH_COMMAND"
Show-Provider "Douyin CLI source" "dy" $douyinTemplate "VMF_DOUYIN_SEARCH_COMMAND"

Write-Host "search CLI data home: $SearchCliHome"
Write-Host "Stage6 source check completed."
