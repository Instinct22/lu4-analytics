#!/bin/bash
# PostgreSQL backup for Lu4 Analytics
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

# Load credentials from .env if present
POSTGRES_USER="${POSTGRES_USER:-lu4}"
POSTGRES_DB="${POSTGRES_DB:-lu4}"
if [ -f .env ]; then
  # shellcheck disable=SC1091
  set -a
  source .env
  set +a
fi

mkdir -p "$BACKUP_DIR"

OUTPUT="$BACKUP_DIR/lu4-db-$TIMESTAMP.dump"

echo "=== Lu4 Analytics - database backup ==="
echo "Compose: $COMPOSE_FILE"
echo "Output:  $OUTPUT"

if ! docker compose -f "$COMPOSE_FILE" ps db --status running -q 2>/dev/null | grep -q .; then
  echo "Error: db container is not running."
  echo "Start it first: docker compose -f $COMPOSE_FILE up -d db"
  exit 1
fi

docker compose -f "$COMPOSE_FILE" exec -T db \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --format=custom \
  --no-owner \
  --no-acl \
  -f /tmp/lu4-backup.dump

docker compose -f "$COMPOSE_FILE" cp "db:/tmp/lu4-backup.dump" "$OUTPUT"
docker compose -f "$COMPOSE_FILE" exec -T db rm -f /tmp/lu4-backup.dump

SIZE_MB="$(du -m "$OUTPUT" | cut -f1)"
echo ""
echo "Done: $OUTPUT (${SIZE_MB} MB)"
echo ""
echo "Copy to another server:"
echo "  scp $OUTPUT root@OTHER_SERVER:/opt/lu4-analytics/backups/"
echo "Restore there:"
echo "  bash scripts/restore-db.sh $OUTPUT"
