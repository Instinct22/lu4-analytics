#!/bin/bash
# Единый запуск Lu4 Analytics на Linux-сервере.
# Usage:
#   bash start.sh
#   bash start.sh --reimport-datasets
#   bash start.sh --fresh-db
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
REIMPORT_DATASETS=0
FRESH_DB=0

for arg in "$@"; do
  case "$arg" in
    --reimport-datasets) REIMPORT_DATASETS=1 ;;
    --fresh-db) FRESH_DB=1 ;;
    -h|--help)
      echo "Usage: bash start.sh [--reimport-datasets] [--fresh-db]"
      echo "  --reimport-datasets  переимпортировать JSON datasets в существующую БД"
      echo "  --fresh-db           удалить volume pgdata и поднять с нуля"
      exit 0
      ;;
    *)
      echo "Неизвестный аргумент: $arg" >&2
      echo "Usage: bash start.sh [--reimport-datasets] [--fresh-db]" >&2
      exit 1
      ;;
  esac
done

echo "=== Lu4 Analytics — запуск ==="
echo "Каталог: $ROOT"
echo "Compose: $COMPOSE_FILE"

# --- Swap (важно на VPS с 2 GB RAM) ---
if [ ! -f /swapfile ] && [ "$(id -u)" -eq 0 ]; then
  MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
  if [ "$MEM_MB" -lt 3500 ]; then
    echo "Мало RAM (${MEM_MB} MB) — создаём swap 2 GB..."
    fallocate -l 2G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab 2>/dev/null; then
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    echo "Swap включён."
  fi
fi

# --- Docker ---
if ! command -v docker &>/dev/null; then
  echo "Установка Docker..."
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

if ! docker compose version &>/dev/null; then
  echo "Ошибка: docker compose не найден." >&2
  exit 1
fi

# --- .env ---
if [ ! -f .env ]; then
  if [ ! -f .env.example ]; then
    echo "Ошибка: нет .env и .env.example" >&2
    exit 1
  fi
  cp .env.example .env
  echo ""
  echo "Создан .env из .env.example — ОБЯЗАТЕЛЬНО смените секреты:"
  echo "  JWT_SECRET, IMPORT_API_KEY, POSTGRES_PASSWORD, CORS_ORIGINS, SEED_USERS"
  echo ""
fi

HTTP_PORT="$(grep -E '^HTTP_PORT=' .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
HTTP_PORT="${HTTP_PORT:-80}"

if grep -qE 'change-me|change-import-key' .env 2>/dev/null; then
  echo "Внимание: в .env остались значения по умолчанию (change-me...)." >&2
  echo "Сгенерируйте секреты: openssl rand -hex 32" >&2
  echo "" >&2
fi

# --- Preflight ---
missing=0
for path in \
  "data/wiki/library" \
  "data/wiki/images" \
  "data/datasets/items_encyclopedia.json" \
  "data/datasets/character_data.json" \
  "data/datasets/duals_catalog.json" \
  "data/datasets/raid_bosses.json"
do
  if [ ! -e "$ROOT/$path" ]; then
    echo "Ошибка: нет $path" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  echo "Распакуйте полный архив (с data/) или скопируйте wiki/datasets." >&2
  exit 1
fi

mkdir -p data/media data/raid-bosses

# --- Остановить старый стек (pgdata не трогаем без --fresh-db) ---
echo ""
echo "Останавливаем предыдущие контейнеры проекта..."
docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
if [ -f docker-compose.yml ]; then
  docker compose -f docker-compose.yml down 2>/dev/null || true
fi

if [ "$FRESH_DB" -eq 1 ]; then
  echo ""
  echo "!!! --fresh-db: будет удалён volume PostgreSQL (все данные БД) !!!"
  echo "Продолжение через 5 секунд... Ctrl+C для отмены."
  sleep 5
  docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true
fi

# Если порт занят чужим docker-контейнером — остановить его
PORT_BUSY="$(docker ps --filter "publish=${HTTP_PORT}" --format '{{.ID}} {{.Names}}' 2>/dev/null || true)"
if [ -n "$PORT_BUSY" ]; then
  echo "Порт ${HTTP_PORT} занят контейнерами — останавливаем:"
  echo "$PORT_BUSY"
  echo "$PORT_BUSY" | awk '{print $1}' | xargs -r docker stop
fi

# --- Лёгкая чистка мусора в каталоге проекта ---
rm -rf frontend/node_modules frontend/dist .pytest_cache backend/.pytest_cache data/reports 2>/dev/null || true
find backend database scripts -type d -name '__pycache__' 2>/dev/null | while read -r d; do rm -rf "$d"; done || true

# --- Сборка и запуск ---
echo ""
echo "Сборка и запуск (первый импорт wiki может занять 10–15 мин)..."
docker compose -f "$COMPOSE_FILE" up -d --build --wait

if [ "$REIMPORT_DATASETS" -eq 1 ]; then
  echo ""
  echo "Переимпорт datasets..."
  docker compose -f "$COMPOSE_FILE" exec -T backend python /scripts/import_datasets.py
fi

# --- Firewall ---
if command -v ufw &>/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
  ufw allow "${HTTP_PORT}/tcp" 2>/dev/null || true
fi

# --- Health ---
echo ""
echo "Проверка /api/health..."
ok=0
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${HTTP_PORT}/api/health" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 2
done

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
ADMIN_HINT="$(grep -E '^SEED_USERS=' .env 2>/dev/null | head -1 | cut -d= -f2- | cut -d: -f1)"
ADMIN_HINT="${ADMIN_HINT:-admin}"

echo ""
echo "============================================"
if [ "$ok" -eq 1 ]; then
  echo "  Статус:      OK (/api/health)"
else
  echo "  Статус:      health ещё не ответил — смотрите логи backend"
fi
echo "  Приложение:  http://${SERVER_IP}:${HTTP_PORT}"
echo "  API docs:    http://${SERVER_IP}:${HTTP_PORT}/api/docs"
echo "  Логин:       ${ADMIN_HINT} / (пароль из SEED_USERS в .env)"
echo "============================================"
echo ""
echo "Полезные команды:"
echo "  docker compose -f $COMPOSE_FILE ps"
echo "  docker compose -f $COMPOSE_FILE logs -f backend"
echo "  docker compose -f $COMPOSE_FILE restart"
echo "  bash start.sh --reimport-datasets"
