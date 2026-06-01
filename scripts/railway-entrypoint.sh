#!/bin/sh
set -e

echo "[startup] Validating environment..."

# Check required API keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[error] OPENAI_API_KEY not set" >&2
    exit 1
fi
echo "[startup] ✓ OPENAI_API_KEY is set"

# Convert Railway/Heroku-style Postgres URLs to SQLAlchemy format
if [ -n "${DATABASE_URL:-}" ]; then
    case "$DATABASE_URL" in
        postgres://*)
            DATABASE_URL="postgresql://${DATABASE_URL#postgres://}"
            echo "[startup] Converted DATABASE_URL from postgres:// to postgresql://"
            ;;
    esac
    export DATABASE_URL
    echo "[startup] ✓ DATABASE_URL is set: ${DATABASE_URL%@*}@..." # Hide password in logs
else
    echo "[startup] ⚠ DATABASE_URL not set, will use SQLite (development mode)"
fi

echo "[startup] Running database migrations..."
if ! alembic -c main_ui/db/migrations/alembic.ini upgrade head; then
    echo "[error] Database migrations failed" >&2
    exit 1
fi
echo "[startup] ✓ Database migrations completed"

PORT="${PORT:-5001}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "[startup] Starting gunicorn..."
echo "[startup] - Port: $PORT"
echo "[startup] - Workers: $WEB_CONCURRENCY"
echo "[startup] - Timeout: ${GUNICORN_TIMEOUT}s"

exec gunicorn main_ui.run_app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  --log-level info

