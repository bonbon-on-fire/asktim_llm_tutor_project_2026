#!/bin/sh
set -e

echo "[startup] database_ui — read-only conversation review dashboard"

# Fail closed: this tool exposes EVERY student's conversations and uploaded
# images, so it must never start without the shared-password gate configured.
if [ -z "${DATABASE_UI_PASSWORD:-}" ]; then
    echo "[error] DATABASE_UI_PASSWORD not set — refusing to start an ungated review tool" >&2
    exit 1
fi
echo "[startup] ✓ DATABASE_UI_PASSWORD is set"

# Session-signing key. The app has an insecure dev default; warn (don't fail) so
# a first deploy still boots, but operators should set this.
if [ -z "${DATABASE_UI_SECRET_KEY:-}" ]; then
    echo "[startup] ⚠ DATABASE_UI_SECRET_KEY not set — using an insecure default; set it for real deploys" >&2
fi

# Normalize Railway/Heroku-style Postgres URLs to the psycopg3 driver. The app
# also does this in Python, but doing it here keeps logs clear and matches the
# other services. DATABASE_UI_DATABASE_URL wins; else DATABASE_URL.
normalize_pg() {
    case "$1" in
        postgres://*)   printf 'postgresql+psycopg://%s' "${1#postgres://}" ;;
        postgresql://*) printf 'postgresql+psycopg://%s' "${1#postgresql://}" ;;
        *)              printf '%s' "$1" ;; # already explicit (or sqlite) — leave as-is
    esac
}
if [ -n "${DATABASE_UI_DATABASE_URL:-}" ]; then
    DATABASE_UI_DATABASE_URL="$(normalize_pg "$DATABASE_UI_DATABASE_URL")"
    export DATABASE_UI_DATABASE_URL
    echo "[startup] ✓ DATABASE_UI_DATABASE_URL set: ${DATABASE_UI_DATABASE_URL%@*}@..." # hide creds
elif [ -n "${DATABASE_URL:-}" ]; then
    DATABASE_URL="$(normalize_pg "$DATABASE_URL")"
    export DATABASE_URL
    echo "[startup] ✓ DATABASE_URL set: ${DATABASE_URL%@*}@..." # hide creds
else
    echo "[error] No DATABASE_UI_DATABASE_URL or DATABASE_URL set" >&2
    exit 1
fi

# Read-only tool: NO migrations, NO create_all. The DB schema is owned by main_ui.

PORT="${PORT:-5003}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"

echo "[startup] Starting gunicorn..."
echo "[startup] - Port: $PORT"
echo "[startup] - Workers: $WEB_CONCURRENCY"

exec gunicorn database_ui.run_app:app \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile - \
  --error-logfile - \
  --log-level info
