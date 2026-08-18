#!/usr/bin/env bash
# Container entrypoint: wait for the database, apply migrations, then serve.
set -euo pipefail

DB_HOST="${DB_HOST:-}"
DB_PORT="${DB_PORT:-5432}"

if [ -n "$DB_HOST" ]; then
  echo "Waiting for database at ${DB_HOST}:${DB_PORT}..."
  ready=false
  for i in $(seq 1 30); do
    if (exec 3<>"/dev/tcp/${DB_HOST}/${DB_PORT}") 2>/dev/null; then
      exec 3>&- 3<&- 2>/dev/null || true
      ready=true
      break
    fi
    sleep 1
  done
  if [ "$ready" = true ]; then
    echo "Database is reachable."
  else
    echo "Database still unreachable after 30s — proceeding anyway; migrations will surface the real error." >&2
  fi
fi

echo "Applying database migrations..."
alembic upgrade head

echo "Starting Reverse ETL API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
