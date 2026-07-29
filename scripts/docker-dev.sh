#!/bin/bash
# Локальный Docker: сборка и обновление из исходников (Linux/macOS).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

CMD="${1:-up}"

if ! command -v docker &>/dev/null; then
  echo "Docker не найден." >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан .env из .env.example"
fi

if [ ! -d data/wiki/library ]; then
  echo "Ошибка: нет data/wiki/library" >&2
  exit 1
fi

HTTP_PORT="$(grep -E '^HTTP_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
HTTP_PORT="${HTTP_PORT:-80}"

case "$CMD" in
  up)
    echo "=== Сборка и запуск локального стека ==="
    docker compose up -d --build --wait
    echo ""
    echo "  Приложение:  http://localhost:${HTTP_PORT}"
    echo "  API docs:    http://localhost:${HTTP_PORT}/api/docs"
    echo "  Логин:       admin / admin123"
    echo ""
    echo "  Backend с hot-reload. После правок UI: bash scripts/docker-dev.sh frontend"
    ;;
  update)
    docker compose build frontend backend
    docker compose up -d frontend backend
    ;;
  frontend)
    docker compose build frontend
    docker compose up -d frontend
    ;;
  backend)
    docker compose build backend
    docker compose up -d backend
    ;;
  dev)
    docker compose --profile dev up -d --build
    echo "  UI hot-reload: http://localhost:5173"
    ;;
  down)
    docker compose --profile dev down
    ;;
  logs)
    docker compose logs -f backend frontend
    ;;
  ps)
    docker compose ps
    ;;
  *)
    echo "Usage: bash scripts/docker-dev.sh [up|update|frontend|backend|dev|down|logs|ps]" >&2
    exit 1
    ;;
esac
