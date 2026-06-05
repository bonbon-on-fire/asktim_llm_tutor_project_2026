#!/bin/sh
set -e

echo "[startup] Validating environment..."

# Check required API keys.
# TEMPORARY: accept OPENAI_KEY as an alias for OPENAI_API_KEY (Railway var is
# currently named OPENAI_KEY). Export the canonical name so libraries that read
# OPENAI_API_KEY directly (e.g. langchain's default env lookup) still work.
if [ -z "${OPENAI_API_KEY:-}" ] && [ -n "${OPENAI_KEY:-}" ]; then
    export OPENAI_API_KEY="$OPENAI_KEY"
    echo "[startup] Using OPENAI_KEY as OPENAI_API_KEY (temporary alias)"
fi
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "[error] OPENAI_API_KEY (or OPENAI_KEY) not set" >&2
    exit 1
fi
echo "[startup] ✓ OPENAI_API_KEY is set"

# Normalize a Railway/Heroku-style Postgres URL to the psycopg3 driver.
# SQLAlchemy's bare postgres:// / postgresql:// scheme defaults to psycopg2,
# which is NOT installed (requirements ships psycopg[binary] == psycopg3). The
# driver must be made explicit as postgresql+psycopg:// or the app crashes on
# boot with ModuleNotFoundError: No module named 'psycopg2' — and data never
# lands in Postgres.
normalize_pg() {
    case "$1" in
        postgres://*)   printf 'postgresql+psycopg://%s' "${1#postgres://}" ;;
        postgresql://*) printf 'postgresql+psycopg://%s' "${1#postgresql://}" ;;
        *)              printf '%s' "$1" ;; # already explicit (or sqlite) — leave as-is
    esac
}

# test_ui resolves its database as TEST_UI_DATABASE_URL -> DATABASE_URL -> SQLite
# (see test_ui/config.py). On Railway the test service references its own Postgres
# via DATABASE_URL. Normalize whichever is set so the effective URL the app picks
# is already psycopg3-ready before gunicorn imports test_ui.run_app:app.
if [ -n "${TEST_UI_DATABASE_URL:-}" ]; then
    TEST_UI_DATABASE_URL="$(normalize_pg "$TEST_UI_DATABASE_URL")"
    export TEST_UI_DATABASE_URL
    echo "[startup] ✓ TEST_UI_DATABASE_URL is set: ${TEST_UI_DATABASE_URL%@*}@..." # Hide host in logs
fi
if [ -n "${DATABASE_URL:-}" ]; then
    DATABASE_URL="$(normalize_pg "$DATABASE_URL")"
    export DATABASE_URL
    echo "[startup] ✓ DATABASE_URL is set: ${DATABASE_URL%@*}@..." # Hide host in logs
fi
if [ -z "${TEST_UI_DATABASE_URL:-}" ] && [ -z "${DATABASE_URL:-}" ]; then
    echo "[startup] ⚠ No database URL set, will use SQLite (development mode — data is ephemeral)"
fi

# No Alembic step for test_ui: the schema is built by Base.metadata.create_all()
# inside create_app(), which runs when gunicorn imports test_ui.run_app:app.
# The target Postgres just needs to exist and be the Sandbox's OWN empty DB
# (main_ui's schema lacks test_ui's syllabus_enabled/custom_* columns, and
# create_all only creates missing tables, never adds columns to existing ones).
echo "[startup] Schema is created on boot via create_all (no migration step)"

PORT="${PORT:-5000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "[startup] Starting gunicorn..."
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
