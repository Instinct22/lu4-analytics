#!/bin/bash
# 0 3 * * * cd /opt/test && bash /opt/test/backup-db.sh >> /opt/backup/lu4-db-backup.log 2>&1
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backup}"
RETAIN_DAYS=7

POSTGRES_USER="${POSTGRES_USER:-lu4}"
POSTGRES_DB="${POSTGRES_DB:-lu4}"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  source .env
  set +a
fi

STAMP=$(date +%Y%m%d_%H%M)
DUMP="${BACKUP_DIR}/lu4-db-${STAMP}.dump"

echo "=== Lu4 Analytics - database backup ==="
echo "Compose: $COMPOSE_FILE"
echo "Target:  $DUMP"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

echo "Starting db container..."
docker compose -f "$COMPOSE_FILE" up -d db

echo "Waiting for PostgreSQL..."
for i in $(seq 1 60); do
  if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "Error: PostgreSQL not ready" >&2
    exit 1
  fi
  sleep 2
done

echo "Creating dump..."
docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$DUMP"

if [ ! -s "$DUMP" ]; then
  echo "Error: empty dump file" >&2
  rm -f "$DUMP"
  exit 1
fi

echo "Removing backups older than ${RETAIN_DAYS} days..."
find "$BACKUP_DIR" -maxdepth 1 -name 'lu4-db-*.dump' -mtime +"${RETAIN_DAYS}" -delete

echo ""
echo "OK: $DUMP ($(du -h "$DUMP" | cut -f1))"
