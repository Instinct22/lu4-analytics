#!/bin/sh
set -eu
cd /opt/lu4-analytics
exec 9>/run/lock/lu4-ci-deploy.lock
flock 9
compose() { docker compose -f docker-compose.prod.yml "$@"; }
compose pull
compose up -d --wait --wait-timeout 2400
# On an existing volume, Compose can report nginx healthy while it is still copying the new data.
attempt=0
until compose exec -T nginx cmp -s /seed/data/datasets/raid_bosses.json /data/datasets/raid_bosses.json; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 120 ]; then
    echo "Timed out waiting for the published raid data" >&2
    exit 1
  fi
  sleep 2
done
compose exec -T backend python /scripts/import_datasets.py raid_bosses
curl --fail --silent --show-error --retry 12 --retry-all-errors http://127.0.0.1/api/health
