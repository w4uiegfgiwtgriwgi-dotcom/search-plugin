param(
  [Parameter(Mandatory = $true)]
  [string]$ArchivePath
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$ResolvedArchive = Resolve-Path $ArchivePath
$DataDir = Join-Path $Root ".local-data"
$BackupDir = Join-Path $Root "backups"

if (-not (Test-Path $BackupDir)) {
  New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

if (Test-Path $DataDir) {
  $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
  $SafetyBackup = Join-Path $BackupDir "before-restore-$Timestamp.zip"
  $SnapshotDir = Join-Path $env:TEMP "video-material-finder-before-restore-$Timestamp"
  if (Test-Path $SnapshotDir) {
    Remove-Item -LiteralPath $SnapshotDir -Recurse -Force
  }
  New-Item -ItemType Directory -Path $SnapshotDir | Out-Null
  Get-ChildItem -LiteralPath $DataDir -Force | ForEach-Object {
    if ($_.Name -eq "video-material-finder.sqlite") {
      return
    }
    Copy-Item -LiteralPath $_.FullName -Destination $SnapshotDir -Recurse -Force
  }
  $DatabasePath = Join-Path $DataDir "video-material-finder.sqlite"
  if (Test-Path $DatabasePath) {
    $SnapshotDatabasePath = Join-Path $SnapshotDir "video-material-finder.sqlite"
    .\.venv\Scripts\python.exe -c "import sqlite3, sys; src, dst = sys.argv[1], sys.argv[2]; source = sqlite3.connect(src); target = sqlite3.connect(dst); source.backup(target); target.close(); source.close()" $DatabasePath $SnapshotDatabasePath
  }
  Compress-Archive -Path (Join-Path $SnapshotDir "*") -DestinationPath $SafetyBackup -CompressionLevel Fastest -Force
  Remove-Item -LiteralPath $SnapshotDir -Recurse -Force
  Write-Host "Current data backed up before restore:"
  Write-Host $SafetyBackup
} else {
  New-Item -ItemType Directory -Path $DataDir | Out-Null
}

Remove-Item -LiteralPath $DataDir -Recurse -Force
New-Item -ItemType Directory -Path $DataDir | Out-Null
Expand-Archive -Path $ResolvedArchive -DestinationPath $DataDir -Force

Write-Host "Data restored from:"
Write-Host $ResolvedArchive
