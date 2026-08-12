$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$DataDir = Join-Path $Root ".local-data"
$BackupDir = Join-Path $Root "backups"

if (-not (Test-Path $DataDir)) {
  throw "missing data directory: .local-data"
}

if (-not (Test-Path $BackupDir)) {
  New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ArchivePath = Join-Path $BackupDir "video-material-finder-data-$Timestamp.zip"
$SnapshotDir = Join-Path $env:TEMP "video-material-finder-backup-$Timestamp"

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

Compress-Archive -Path (Join-Path $SnapshotDir "*") -DestinationPath $ArchivePath -CompressionLevel Fastest -Force
Remove-Item -LiteralPath $SnapshotDir -Recurse -Force

Write-Host "Backup created:"
Write-Host $ArchivePath
