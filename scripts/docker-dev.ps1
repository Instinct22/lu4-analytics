# Локальный Docker: сборка и обновление из исходников (Windows).
# Usage:
#   .\scripts\docker-dev.ps1              # первый запуск / полная пересборка
#   .\scripts\docker-dev.ps1 update     # пересобрать frontend + backend
#   .\scripts\docker-dev.ps1 frontend     # только UI (после правок React)
#   .\scripts\docker-dev.ps1 backend      # только backend-образ
#   .\scripts\docker-dev.ps1 dev          # vite hot-reload на :5173
#   .\scripts\docker-dev.ps1 down
#   .\scripts\docker-dev.ps1 logs

param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "update", "frontend", "backend", "dev", "down", "logs", "ps")]
    [string]$Command = "up"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker не найден. Установите Docker Desktop."
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Создан .env из .env.example"
}

if (-not (Test-Path "data/wiki/library")) {
    Write-Error "Нет data/wiki/library — положите wiki-данные в data/"
}

function Invoke-Compose {
    param([string[]]$Args)
    docker compose @Args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Command) {
    "up" {
        Write-Host "=== Сборка и запуск локального стека ===" -ForegroundColor Cyan
        Invoke-Compose @("up", "-d", "--build", "--wait")
        $port = (Get-Content .env | Where-Object { $_ -match '^HTTP_PORT=' } | ForEach-Object { $_ -replace '^HTTP_PORT=', '' })
        if (-not $port) { $port = "80" }
        Write-Host ""
        Write-Host "  Приложение:  http://localhost:$port" -ForegroundColor Green
        Write-Host "  API docs:    http://localhost:$port/api/docs"
        Write-Host "  Логин:       admin / admin123"
        Write-Host ""
        Write-Host "  Backend с hot-reload (DEV_RELOAD=true)."
        Write-Host "  После правок UI:  .\scripts\docker-dev.ps1 frontend"
    }
    "update" {
        Write-Host "=== Пересборка frontend + backend ===" -ForegroundColor Cyan
        Invoke-Compose @("build", "frontend", "backend")
        Invoke-Compose @("up", "-d", "frontend", "backend")
        Write-Host "Готово." -ForegroundColor Green
    }
    "frontend" {
        Write-Host "=== Пересборка frontend ===" -ForegroundColor Cyan
        Invoke-Compose @("build", "frontend")
        Invoke-Compose @("up", "-d", "frontend")
        Write-Host "Frontend обновлён." -ForegroundColor Green
    }
    "backend" {
        Write-Host "=== Пересборка backend (обычно не нужна — код монтируется) ===" -ForegroundColor Cyan
        Invoke-Compose @("build", "backend")
        Invoke-Compose @("up", "-d", "backend")
        Write-Host "Backend обновлён." -ForegroundColor Green
    }
    "dev" {
        Write-Host "=== Dev-режим: Vite hot-reload на :5173 ===" -ForegroundColor Cyan
        Invoke-Compose @("--profile", "dev", "up", "-d", "--build")
        Write-Host ""
        Write-Host "  UI (hot-reload): http://localhost:5173" -ForegroundColor Green
        Write-Host "  API через nginx: http://localhost (порт из HTTP_PORT в .env)"
    }
    "down" {
        Invoke-Compose @("down")
    }
    "logs" {
        Invoke-Compose @("logs", "-f", "backend", "frontend")
    }
    "ps" {
        Invoke-Compose @("ps")
    }
}
