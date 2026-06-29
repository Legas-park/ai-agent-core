#!/bin/sh
set -e

if [ -n "${DATABASE_URL}" ]; then
  echo "Running database migrations..."
  alembic upgrade head
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
