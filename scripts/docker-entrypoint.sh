#!/bin/bash
set -e

cd /database
alembic -c alembic.ini upgrade head

cd /app
python /scripts/seed_users.py

python /scripts/import_wiki.py --if-empty

if [ "${DEV_RELOAD:-false}" = "true" ]; then
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
else
  # UVICORN_WORKERS=1 recommended on 2 GB RAM VPS; use 2+ on 4 GB+
  exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-1}"
fi
