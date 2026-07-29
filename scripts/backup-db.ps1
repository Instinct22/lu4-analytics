# PostgreSQL backup for Lu4 Analytics (Windows)
param(
    [string]$ComposeFile = "docker-compose.prod.yml",
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$BackupDir = Join-Path $Root "backups"
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
if (-not $Output) {
    $Output = Join-Path $BackupDir "lu4-db-$Timestamp.dump"
}

$PostgresUser = "lu4"
$PostgresDb = "lu4"
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*POSTGRES_USER=(.+)$') { $PostgresUser = $Matches[1].Trim() }
        if ($_ -match '^\s*POSTGRES_DB=(.+)$') { $PostgresDb = $Matches[1].Trim() }
    }
}

Write-Host "=== Lu4 Analytics - database backup ===" -ForegroundColor Cyan
Write-Host "Compose: $ComposeFile"
Write-Host "Output:  $Output"

$running = docker compose -f $ComposeFile ps db --status running -q 2>$null
if (-not $running) {
    Write-Error "db container is not running. Start: docker compose -f $ComposeFile up -d db"
}

docker compose -f $ComposeFile exec -T db `
    pg_dump -U $PostgresUser -d $PostgresDb `
    --format=custom `
    --no-owner `
    --no-acl `
    -f /tmp/lu4-backup.dump

docker compose -f $ComposeFile cp "db:/tmp/lu4-backup.dump" $Output
docker compose -f $ComposeFile exec -T db rm -f /tmp/lu4-backup.dump

$SizeMb = [math]::Round((Get-Item $Output).Length / 1MB, 1)
Write-Host ""
Write-Host "Done: $Output ($SizeMb MB)" -ForegroundColor Green
Write-Host ""
Write-Host "Copy to another server:" -ForegroundColor Cyan
Write-Host "  scp `"$Output`" root@OTHER_SERVER:/opt/lu4-analytics/backups/"
Write-Host "Restore there:" -ForegroundColor Cyan
Write-Host "  bash scripts/restore-db.sh backups/lu4-db-*.dump"
