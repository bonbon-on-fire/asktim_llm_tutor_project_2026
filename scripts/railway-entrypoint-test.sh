#!/bin/sh
set -e

echo "[startup] Validating environment..."

# Check required API keys
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[error] OPENAI_API_KEY not set" >&2
    exit 1
fi
echo "[startup] ✓ OPENAI_API_KEY is set"

# test_ui reads TEST_UI_DATABASE_URL (kept separate from main_ui's DATABASE_URL).
# Normalize Railway/Heroku-style Postgres URLs to the psycopg3 driver — the app
# ships psycopg[binary] (psycopg3), so a bare postgresql:// (which SQLAlchemy
# maps to psycopg2) would crash with ModuleNotFoundError: No module named 'psycopg2'.
if [ -n "${TEST_UI_DATABASE_URL:-}" ]; then
    case "$TEST_UI_DATABASE_URL" in
        postgres://*)
            TEST_UI_DATABASE_URL="postgresql+psycopg://${TEST_UI_DATABASE_URL#postgres://}"
            echo "[startup] Converted TEST_UI_DATABASE_URL postgres:// -> postgresql+psycopg://"
            ;;
        postgresql+psycopg://*)
            ;; # already explicit, leave as-is
        postgresql://*)
            TEST_UI_DATABASE_URL="postgresql+psycopg://${TEST_UI_DATABASE_URL#postgresql://}"
            echo "[startup] Converted TEST_UI_DATABASE_URL postgresql:// -> postgresql+psycopg://"
            ;;
    esac
    export TEST_UI_DATABASE_URL
    echo "[startup] ✓ TEST_UI_DATABASE_URL is set: ${TEST_UI_DATABASE_URL%@*}@..." # Hide password in logs
else
    echo "[startup] ⚠ TEST_UI_DATABASE_URL not set, will use SQLite (development mode)"
fi

# test_ui builds its schema with Base.metadata.create_all on boot (no Alembic),
# so there is no separate migration step here — the database just needs to exist.

PORT="${PORT:-5000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "[startup] Starting gunicorn (test_ui)..."
echo "[startup] - Port: $PORT"
echo "[startup] - Workers: $WEB_CONCURRENCY"
echo "[startup] - Timeout: ${GUNICORN_TIMEOUT}s"

exec gunicorn test_ui.run_app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  --log-level info
