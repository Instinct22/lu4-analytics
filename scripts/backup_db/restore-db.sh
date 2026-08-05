#!/bin/bash
# Restore PostgreSQL backup on Lu4 Analytics
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DUMP_FILE="${1:-}"

POSTGRES_USER="${POSTGRES_USER:-lu4}"
POSTGRES_DB="${POSTGRES_DB:-lu4}"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  source .env
  set +a
fi

if [ -z "$DUMP_FILE" ]; then
  echo "Usage: bash scripts/restore-db.sh <path-to.dump>"
  echo ""
  echo "Available backups:"
  echo "  /opt/backup:"
  ls -lh /opt/backup/lu4-db-*.dump 2>/dev/null || echo "    (none)"
  echo "  backups/:"
  ls -lh backups/lu4-db-*.dump 2>/dev/null || echo "    (none)"
  exit 1
fi

if [ ! -f "$DUMP_FILE" ]; then
  echo "Error: file not found: $DUMP_FILE"
  exit 1
fi

echo "=== Lu4 Analytics - database restore ==="
echo "Compose: $COMPOSE_FILE"
echo "Dump:    $DUMP_FILE"
echo ""
echo "WARNING: this will replace all data in database '$POSTGRES_DB'."
read -r -p "Continue? [y/N] " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "Cancelled."
  exit 0
fi

echo "Starting db container..."
docker compose -f "$COMPOSE_FILE" up -d db

echo "Waiting for PostgreSQL..."
for i in $(seq 1 60); do
  if docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo "Dropping and recreating schema..."
docker compose -f "$COMPOSE_FILE" exec -T db psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "$POSTGRES_DB";
CREATE DATABASE "$POSTGRES_DB";
SQL

echo "Restoring dump (may take a few minutes)..."
docker compose -f "$COMPOSE_FILE" cp "$DUMP_FILE" "db:/tmp/lu4-restore.dump"
docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --no-owner \
  --no-acl \
  /tmp/lu4-restore.dump
docker compose -f "$COMPOSE_FILE" exec -T db rm -f /tmp/lu4-restore.dump

echo ""
echo "Restarting backend..."
docker compose -f "$COMPOSE_FILE" up -d backend

echo ""
echo "Done. Database restored from: $DUMP_FILE"
echo "Check: curl http://localhost/api/health"
