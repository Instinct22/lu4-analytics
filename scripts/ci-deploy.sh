#!/bin/sh
set -eu
cd /opt/lu4-analytics
exec 9>/run/lock/lu4-ci-deploy.lock
flock 9
compose() { docker compose -f docker-compose.prod.yml "$@"; }
compose pull
compose up -d --wait --wait-timeout 2400
compose exec -T backend python /scripts/import_datasets.py raid_bosses
curl --fail --silent --show-error --retry 12 --retry-all-errors http://127.0.0.1/api/health
