# Pack Lu4 Analytics for server deployment (Windows, no Git required)
# Usage:
#   .\scripts\pack-for-deploy.ps1                  # код + data (по умолчанию)
#   .\scripts\pack-for-deploy.ps1 -NoData          # только код
#   .\scripts\pack-for-deploy.ps1 -SkipRawHtml     # без library\raw (~650 MB)
param(
    # Не включать data\wiki, data\datasets, data\raid-bosses
    [switch]$NoData,
    # Leave out library\raw (~650 MB). Safe once npc_loot is imported on the server:
    # loot is served from the database and raw HTML is only needed to (re)parse it.
    [switch]$SkipRawHtml,
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$IncludeData = -not $NoData

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Timestamp = Get-Date -Format "yyyyMMdd-HHmm"
$DefaultOutput = Join-Path $Root ("dist\lu4-analytics-{0}.tar.gz" -f $Timestamp)
if (-not $Output) { $Output = $DefaultOutput }

$DistDir = Split-Path $Output -Parent
if (-not (Test-Path $DistDir)) {
    New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
}

Write-Host "=== Lu4 Analytics - pack for deploy ===" -ForegroundColor Cyan
Write-Host ("Project: {0}" -f $Root)
Write-Host ("Output:  {0}" -f $Output)
Write-Host ("Data:    {0}" -f ($(if ($IncludeData) { "yes" } else { "no (-NoData)" })))

if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
    Write-Error "Command tar not found. On Windows 10/11 it is built-in. Or use WSL."
}

$Staging = Join-Path $DistDir ".pack-staging"
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path $Staging -Force | Out-Null

function Copy-TreeFiltered {
    param(
        [string]$SrcRel,
        [string]$DstRel,
        [string[]]$ExcludeDirs = @()
    )
    $src = Join-Path $Root $SrcRel
    if (-not (Test-Path $src)) { return $false }
    $dst = Join-Path $Staging $DstRel
    $parent = Split-Path $dst -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $excluded = @(
        "node_modules", "__pycache__", ".venv", ".pytest_cache",
        "dist", ".git", "tests", "reports"
    ) + $ExcludeDirs
    $null = robocopy $src $dst /E /NFL /NDL /NJH /NJS /nc /ns /np `
        /XD $excluded `
        /XF *.pyc .DS_Store server-secrets.*
    if ($LASTEXITCODE -ge 8) {
        Write-Error ("robocopy failed for {0} (exit {1})" -f $SrcRel, $LASTEXITCODE)
    }
    return $true
}

Write-Host ""
Write-Host "Copying project files (excluding node_modules, caches, tests)..."

$Copied = @()
foreach ($dir in @("backend", "frontend", "database", "scripts", "nginx")) {
    if (Copy-TreeFiltered $dir $dir) { $Copied += $dir }
}

foreach ($file in @(
    "start.sh",
    "docker-compose.yml",
    "docker-compose.prod.yml",
    ".env.example",
    "README.md",
    "DEPLOY.md"
)) {
    $src = Join-Path $Root $file
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $Staging $file) -Force
        $Copied += $file
    }
}

$dataDir = Join-Path $Staging "data"
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $dataDir "media") -Force | Out-Null
"" | Set-Content (Join-Path $dataDir ".gitkeep")
"" | Set-Content (Join-Path $dataDir "media\.gitkeep")

if ($IncludeData) {
    Write-Host "Packing data\wiki, data\datasets, data\raid-bosses ..."
    $wikiExcludes = @()
    if ($SkipRawHtml) {
        $wikiExcludes += (Join-Path $Root "data\wiki\library\raw")
        Write-Host "Skipping library\raw - npc_loot must already be imported." -ForegroundColor Yellow
    }
    if (Copy-TreeFiltered "data\wiki" "data\wiki" $wikiExcludes) { $Copied += "data/wiki" }
    if (Copy-TreeFiltered "data\datasets" "data\datasets") { $Copied += "data/datasets" }
    if (Copy-TreeFiltered "data\raid-bosses" "data\raid-bosses") { $Copied += "data/raid-bosses" }
    if ($Copied -notcontains "data/wiki") {
        Write-Warning "data\wiki not found. Deploy will fail until wiki data is present."
    }
    if ($Copied -notcontains "data/datasets") {
        Write-Warning "data\datasets not found. Deploy will fail until datasets are present."
    }
}
else {
    Write-Host ""
    Write-Host "Wiki data NOT included (-NoData). Copy data\wiki, data\datasets, data\raid-bosses separately." -ForegroundColor Yellow
}

if ($Copied.Count -eq 0) {
    Write-Error "Nothing to pack."
}

# Normalize start.sh line endings for Linux
$startSh = Join-Path $Staging "start.sh"
if (Test-Path $startSh) {
    $text = [System.IO.File]::ReadAllText($startSh) -replace "`r`n", "`n" -replace "`r", "`n"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($startSh, $text, $utf8NoBom)
}

Write-Host ""
Write-Host "Creating archive..."
if (Test-Path $Output) { Remove-Item $Output -Force }

Push-Location $Staging
try {
    & tar -czf $Output *
    if ($LASTEXITCODE -ne 0) {
        Write-Error "tar failed."
    }
}
finally {
    Pop-Location
    Remove-Item $Staging -Recurse -Force -ErrorAction SilentlyContinue
}

$SizeMb = [math]::Round((Get-Item $Output).Length / 1MB, 1)
Write-Host ""
Write-Host ("Done: {0} ({1} MB)" -f $Output, $SizeMb) -ForegroundColor Green
Write-Host ""
Write-Host "=== Next steps ===" -ForegroundColor Cyan
Write-Host "1. Copy archive to server:"
Write-Host ("   scp `"{0}`" root@SERVER_IP:/opt/" -f $Output)
Write-Host ""
Write-Host "2. On server: replace old install (see DEPLOY.md), then:"
Write-Host "   ssh root@SERVER_IP"
Write-Host "   # stop + backup .env/media + extract into clean /opt/lu4-analytics"
Write-Host "   bash start.sh"
Write-Host ""
Write-Host "Full guide: DEPLOY.md"

if (-not $IncludeData) {
    Write-Host ""
    Write-Host "Also copy data separately:" -ForegroundColor Yellow
    Write-Host "   scp -r data\wiki data\datasets data\raid-bosses root@SERVER_IP:/opt/lu4-analytics/data/"
}
