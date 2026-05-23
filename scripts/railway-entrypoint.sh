#!/bin/sh
set -e

# Railway/Heroku-style Postgres URLs use postgres://; SQLAlchemy expects postgresql://.
if [ -n "${DATABASE_URL:-}" ]; then
  case "$DATABASE_URL" in
    postgres://*) DATABASE_URL="postgresql://${DATABASE_URL#postgres://}" ;;
  esac
  export DATABASE_URL
fi

echo "Running database migrations..."
alembic -c main_ui/db/migrations/alembic.ini upgrade head

PORT="${PORT:-5001}"
echo "Starting gunicorn on 0.0.0.0:${PORT}..."

exec gunicorn main_ui.run_app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
