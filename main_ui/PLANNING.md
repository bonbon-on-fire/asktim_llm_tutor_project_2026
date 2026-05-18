# main_ui — Implementation Planning

Step-by-step build plan for `main_ui/`, the production-shape embeddable tutor app.

For the overall design (problem, decisions, schema, routes, identity flow, non-goals), see [Phase 8 of the main PLANNING.md](../PLANNING.md). This file tracks **how each step gets built**, in order.

---

## Step 1: Folder skeleton + Flask app + `python -m main_ui` boots ✦ COMPLETED

**Goal:** Create the minimal package structure and a Flask app that responds to a health check. No database, no chat, no templates yet — just confirm the package is importable, the server boots on port 5001, and `python -m main_ui` works end to end.

This is the foundation every other step builds on. Keep it tiny and obviously correct.

### Files to create

```text
main_ui/
  __init__.py           # empty package marker
  __main__.py           # python -m main_ui entry point
  run_app.py            # Flask app factory + health check route
  config.py             # env-driven config dataclass
  README.md             # quick start, env vars, comparison with web_ui
  PLANNING.md           # this file
```

No subfolders yet — `db/`, `routes/`, `services/`, `templates/`, `static/`, `uploads/`, `tests/` are added in later steps.

### Purpose of each file

**`main_ui/__init__.py`**
- **Purpose:** marks `main_ui/` as a Python package so it can be imported and run as `python -m main_ui`.
- **Owns:** nothing (empty file).
- **Used by:** Python's import machinery; every other file in the package.

**`main_ui/config.py`**
- **Purpose:** central place for environment-driven settings. Reads env vars once at startup and returns a frozen, type-checked config object the rest of the app uses.
- **Owns:** the `Config` shape — currently `secret_key`, `database_url`, `port`. New settings (Postgres pool size, upload limits, CSP origins, etc.) get added here in later steps.
- **Defaults:** dev-friendly fallbacks for every value so the app boots without an `.env` file (`dev-insecure-key`, local SQLite path, port 5001).
- **Why a dataclass:** explicit fields, type hints, immutable, easy to unit-test by constructing a `Config` directly.
- **Used by:** `run_app.py` (to set Flask's `SECRET_KEY`) and `__main__.py` (to choose the port). Later steps add DB engine creation in Step 2.

**`main_ui/run_app.py`**
- **Purpose:** Flask app factory. The single function `create_app()` builds and returns a configured Flask instance. Importing `app` at module level gives gunicorn (and tests, and any other importer) a ready-to-use WSGI object.
- **Owns:** Flask app construction, route registration, and any app-level middleware/teardown wiring.
- **In Step 1:** registers exactly one route — `GET /health` returning `{"status": "ok", "service": "main_ui"}`. Later steps add blueprints from `routes/`, DB session lifecycle, error handlers, CSP headers, etc.
- **Factory-pattern rationale:** keeps testing easy (each test can `create_app()` with a different config) and avoids module-import side effects beyond the single `app = create_app()` line.

**`main_ui/__main__.py`**
- **Purpose:** entry point for `python -m main_ui`. Boots Flask's development server on the configured port with debug mode enabled.
- **Owns:** nothing the app needs at runtime — it's just glue between the CLI invocation and the Flask app.
- **Not used in production:** the production path is `gunicorn main_ui.run_app:app`. This file exists purely for local dev convenience.
- **Why a separate file:** standard Python convention — `python -m <package>` looks for `<package>/__main__.py`. Keeps the boot command tiny.

**`main_ui/README.md`**
- **Purpose:** quick-reference doc for a developer who has never touched this folder before. Covers what `main_ui/` is, how to boot it, how to verify it's running, and how it differs from `web_ui/`.
- **Owns:** local dev quick-start (`python -m main_ui`), health-check URL, supported env vars (`MAIN_UI_SECRET_KEY`, `DATABASE_URL`, `PORT`), and a short comparison with `web_ui/` (with a link to the Phase 8 comparison table in the root `PLANNING.md`).
- **Grows over time:** later steps add sections for DB migrations (Step 2), iframe testing (Step 10), running tests (Step 11), etc.

**`main_ui/PLANNING.md`** *(this file)*
- **Purpose:** the implementation roadmap for `main_ui/`. The root `PLANNING.md` says *what* Phase 8 is and *why*; this file says *how* it gets built, step by step.
- **Owns:** the ordered step list, acceptance criteria for each step, and the running record of which step is active.
- **Lives inside `main_ui/`:** keeps build planning next to the code it describes, mirroring the pattern of `meeting_notes/` and `docs/` co-located with their context.

### Dependencies

- **Flask** — already in the root `requirements.txt` (used by `web_ui/`). No new packages for Step 1.
- **Python 3.11+** (assumed; matches project baseline).

### Acceptance criteria

1. `python -m main_ui` boots and prints Flask's "Running on http://127.0.0.1:5001" banner.
2. `curl http://127.0.0.1:5001/health` returns HTTP 200 with body `{"status": "ok", "service": "main_ui"}`.
3. No port collision with `web_ui` (which uses port 5000).
4. No imports from `web_ui/`, `tutor/`, `students/`, or `judge/` yet — Step 1 stays fully self-contained.
5. `from main_ui.run_app import app` works from anywhere in the repo (for future gunicorn compatibility).
6. The Flask app uses the factory pattern (`create_app()`) so later steps can wire in DB session, blueprints, etc. without rewriting boot code.

### Verification steps

```powershell
# Boot the app
python -m main_ui

# In a second terminal, hit the health endpoint
curl http://127.0.0.1:5001/health

# Expected response:
# {"service":"main_ui","status":"ok"}

# Confirm no port conflict by also running web_ui (optional)
python -m web_ui    # binds to 5000
# Both apps should coexist
```

### What's deliberately NOT in Step 1

- No `db/` folder, no SQLAlchemy, no Postgres connection — that's Step 2
- No `/embed` route, no chat HTML, no static assets — Step 3+
- No tutor integration (`tutor.run_tutor`) — Step 4
- No `/api/chat` endpoint — Step 5
- No frontend code — Step 6
- No email modal, identity, or cookies — Step 7
- No history sidebar — Step 8
- No image uploads — Step 9
- No `test_host.html` — Step 10
- No tests — Step 11

### Risks / gotchas

- **Port mismatch**: If `PORT` env var is set to something other than 5001 (e.g. by another tool), the app picks that up. Document the override behavior in the README so it's obvious.
- **Flask debug mode**: We're keeping `debug=True` for dev convenience. Document that production hosting (when it comes) must turn this off.
- **`SECRET_KEY`**: Defaults to `"dev-insecure-key"`. Fine for local dev. Note in README that production needs a real key.

---

## Step 2: Database schema + Alembic migrations + SQLAlchemy models ✦ ACTIVE

**Goal:** Stand up the persistence layer. Define SQLAlchemy 2.x models for `Conversation`, `Message`, and `UploadedImage`. Wire Alembic so we can version the schema. Get `alembic upgrade head` working against both SQLite (the dev default, zero setup) and PostgreSQL (via Docker, mirrors production). No HTTP routes touch the DB yet — that's Step 3+.

This step makes the database real but doesn't connect it to the Flask app yet. Engine + session wiring into `run_app.py` happens in Step 3 when the first route actually needs to read/write.

#### Files to create

```text
main_ui/
  db/
    __init__.py                          # package marker; re-exports public API
    models.py                            # SQLAlchemy 2.x DeclarativeBase + 3 model classes
    session.py                           # engine + session factory built from config.database_url
    migrations/
      alembic.ini                        # Alembic configuration
      env.py                             # imports Base.metadata; reads DATABASE_URL at run time
      script.py.mako                     # Alembic's revision template
      versions/
        <hash>_initial_schema.py         # autogenerated first migration
```

Plus a small touch-up to the root `requirements.txt` to add the new deps.

#### Purpose of each file

**`main_ui/db/__init__.py`**
- **Purpose:** package marker and public API surface for the `db` subpackage. Re-exports `Base`, the three model classes (`Conversation`, `Message`, `UploadedImage`), and the session helpers (`engine`, `SessionLocal`, `get_session`).
- **Why a re-export hub:** callers write `from main_ui.db import Conversation` without caring about whether the class lives in `models.py` or somewhere else. Lets us split files later without breaking imports.

**`main_ui/db/models.py`**
- **Purpose:** the single source of truth for the database schema. Declares the SQLAlchemy 2.x `DeclarativeBase` and the three ORM classes that mirror the tables described in Phase 8 of the root `PLANNING.md`.
- **Owns:**
  - `Base` — declarative base shared by every model
  - `Conversation` — `id` (UUID, Python-generated), `session_id`, `email` (nullable), `course`, `exercise_number`, `tutor_prompt`, `started_at`, `last_active_at`
  - `Message` — `id` (BigInteger), `conversation_id` (FK → Conversation, cascade delete), `turn`, `role` (CHECK constraint: `'student'` or `'tutor'`), `content`, `pedagogical_reasoning` (nullable, only set for tutor rows), `created_at`
  - `UploadedImage` — `id` (BigInteger), `message_id` (FK → Message, cascade delete), `filename`, `mime_type`, `size_bytes`, `created_at`
- **Relationships:** `Conversation.messages` (one-to-many), `Message.uploaded_images` (one-to-many). Both with `cascade="all, delete-orphan"` so deleting a Conversation cleans up its messages and their images.
- **Indexes:** `email` and `session_id` on `conversations`; `conversation_id` on `messages`; `message_id` on `uploaded_images` (the last comes for free with the FK in Postgres but is explicit for SQLite).
- **Portable types:**
  - UUIDs use SQLAlchemy 2.x `Uuid(as_uuid=True)` — Postgres stores native UUID, SQLite stores TEXT, ORM exposes `uuid.UUID` either way.
  - Timestamps use `DateTime(timezone=True)` — Postgres uses TIMESTAMPTZ; SQLite has no timezone support but the ORM layer normalizes Python-side datetimes to UTC before writing.
  - UUID generation is Python-side (`default=uuid.uuid4`) so we don't depend on `gen_random_uuid()` (Postgres-only).

**`main_ui/db/session.py`**
- **Purpose:** build the SQLAlchemy engine and session factory from `config.database_url`. One place that knows how to connect to the DB.
- **Owns:**
  - `engine` — module-level singleton built lazily from `load_config().database_url`
  - `SessionLocal` — `sessionmaker` bound to the engine
  - `get_session()` — context manager that yields a session and commits/rolls-back on exit
- **Cross-driver handling:**
  - For SQLite URLs: passes `connect_args={"check_same_thread": False}` so the Flask dev server can share connections across request threads
  - For Postgres URLs (`postgresql+psycopg://...`): standard pooling, no special connect args
- **Not yet wired into Flask:** Step 3 imports `SessionLocal` from here when `/api/whoami` is added. Until then, this module is exercise-able only via Alembic and ad-hoc Python.

**`main_ui/db/migrations/alembic.ini`**
- **Purpose:** Alembic's main config file. Tells Alembic where to find `env.py`, the script template, and the `versions/` dir. Logging config also lives here.
- **Notable:** the `sqlalchemy.url` line is intentionally **empty** — `env.py` reads `DATABASE_URL` from the environment at run time instead of hardcoding it. This is what makes the same migration script work against SQLite and Postgres.
- **Invocation:** all migration commands point at this file explicitly — `alembic -c main_ui/db/migrations/alembic.ini upgrade head`.

**`main_ui/db/migrations/env.py`**
- **Purpose:** Alembic's environment script — the glue between Alembic and our SQLAlchemy models. Imports `Base.metadata` from `main_ui.db.models`, reads `DATABASE_URL` from the environment, and wires both into Alembic's context.
- **Owns:** the offline (SQL-script generation) and online (direct execution) Alembic modes. Both modes call `Base.metadata` as `target_metadata` so `alembic revision --autogenerate` can detect new/changed models.

**`main_ui/db/migrations/script.py.mako`**
- **Purpose:** Alembic's template file for new revision scripts. Used by `alembic revision`/`alembic revision --autogenerate`.
- **Owns:** nothing project-specific — usually copied verbatim from `alembic init`. We keep it untouched unless we want to customize the generated docstrings or imports.

**`main_ui/db/migrations/versions/<hash>_initial_schema.py`**
- **Purpose:** the first migration. Creates the three tables, their indexes, the FK constraints, and the CHECK constraint on `messages.role`.
- **Generated, then hand-reviewed:** we run `alembic revision --autogenerate -m "initial schema"`, then read the result top to bottom and fix anything autogen misses (autogenerate is good but not perfect — CHECK constraints and some index naming sometimes need manual touch-up).
- **Note on UUID columns:** verify the autogenerated `op.create_table(... sa.Uuid())` works on both backends. If not, drop in `sa.String(36)` with a converter at the ORM layer instead.

**Root `requirements.txt` additions**
- `sqlalchemy>=2.0` — the ORM
- `alembic` — schema migrations
- `psycopg[binary]>=3.1` — PostgreSQL driver. Used by Postgres backend; SQLite uses the stdlib `sqlite3` and needs no extra package.

#### Dependencies

- **SQLAlchemy 2.x** (uses 2.0 typed declarative style, not the legacy 1.x style)
- **Alembic** (pairs naturally with SQLAlchemy)
- **psycopg v3** (`psycopg[binary]`) — modern, async-capable Postgres driver; binary wheel avoids needing a system C compiler
- **Docker** (only when testing against Postgres locally) — `docker run --name tutor-postgres -e POSTGRES_PASSWORD=dev -e POSTGRES_DB=tutor -p 5432:5432 -d postgres:16`

#### Cross-backend portability

This is the riskiest part of Step 2 because dev (SQLite) and production (Postgres) behave differently in subtle ways.

| Concern | SQLite behavior | Postgres behavior | How we handle it |
| --- | --- | --- | --- |
| UUID primary keys | Stored as TEXT | Native UUID | `sa.Uuid(as_uuid=True)` + Python-side `default=uuid.uuid4` |
| `BIGSERIAL` / autoincrement | `INTEGER PRIMARY KEY AUTOINCREMENT` | `BIGSERIAL` | `Mapped[int] = mapped_column(BigInteger, primary_key=True)` — SQLAlchemy emits the right thing per dialect |
| `TIMESTAMPTZ` | No timezone support (stores naive datetime) | Native | `DateTime(timezone=True)` + always write tz-aware datetimes in Python |
| `gen_random_uuid()` | Doesn't exist | Native | Generate UUIDs in Python, not in the DB default |
| CHECK constraints | Supported | Supported | Same definition works for both |
| Foreign-key cascade | Must enable per-connection (`PRAGMA foreign_keys=ON`) | On by default | Set `connect_args={"check_same_thread": False}` + listen for `connect` events to enable FK enforcement on SQLite |
| Connection pooling | Not relevant (single-file DB) | Real pooling needed | Default SQLAlchemy pool is fine for both at our scale |

#### Acceptance criteria

1. `from main_ui.db import Base, Conversation, Message, UploadedImage, SessionLocal, get_session` imports cleanly from any working directory.
2. `alembic -c main_ui/db/migrations/alembic.ini upgrade head` succeeds against the default SQLite URL (`sqlite:///./main_ui.db`) and produces a file with the three tables.
3. The same command succeeds against a Dockerized Postgres (`postgresql+psycopg://postgres:dev@localhost:5432/tutor`) — `DATABASE_URL` env var is the only thing that changes.
4. After `upgrade head`, all three tables exist with the correct columns, FK constraints, CHECK constraint on `messages.role`, and the four named indexes.
5. Round-trip test passes: insert a Conversation → insert a Message linked to it → insert an UploadedImage linked to the Message → query all three back → delete the Conversation → confirm cascade removed the Message and UploadedImage rows.
6. `alembic downgrade base` cleanly drops all three tables (round-trip reversibility — useful when iterating in dev).

#### Verification steps (manual)

1. Run `pip install -r requirements.txt` after adding the new deps.
2. Apply the migration against SQLite (no setup): `alembic -c main_ui/db/migrations/alembic.ini upgrade head`. Inspect `main_ui.db` with the SQLite browser of your choice (or `sqlite3 main_ui.db ".tables"`) and confirm three tables.
3. Start a Postgres container, switch `DATABASE_URL` to point at it, re-run the same upgrade command, and confirm the same tables exist (`psql ... -c "\dt"`).
4. Run a short ad-hoc Python session that imports the models, opens a session via `get_session()`, performs the round-trip insert/query/delete described in acceptance criterion 5.

#### What's deliberately NOT in Step 2

- **Flask integration of the engine/session lifecycle** — Step 3 adds `SessionLocal()` per-request handling once a route actually uses the DB.
- **`flask-sqlalchemy`** — we use plain SQLAlchemy 2.x; the Flask integration helper would be a separate concern and is not needed yet.
- **Model methods or business logic** — models are dumb data shapes here. Conversation create/append logic lives in `main_ui/services/conversation.py` later.
- **Per-conversation last-active-timestamp updates** — wired in Step 5 when chat actually mutates conversations.
- **Tests** — Step 11.
- **Production Postgres setup** — local Docker only; managed-DB provisioning is a later phase.

#### Risks / gotchas

- **Autogenerate quirks:** Alembic's `--autogenerate` doesn't always detect CHECK constraints or some index renames. Always read the generated migration top-to-bottom before committing it.
- **SQLite FK enforcement:** SQLite ships with FK enforcement *off* by default. If we don't enable it via a `PRAGMA foreign_keys=ON` listener in `session.py`, our cascade-delete tests will silently fail.
- **UUID display:** SQLite stores UUIDs as TEXT (hyphenated strings); Postgres stores them as native UUID. The ORM layer normalizes both to `uuid.UUID`, but raw `SELECT *` output looks different between the two — don't be alarmed.
- **Timezone confusion:** Python's `datetime.utcnow()` is timezone-*naive*. We must use `datetime.now(timezone.utc)` (or equivalent) so the values written are tz-aware and Postgres-friendly.
- **Migration script must be committed:** the generated `versions/<hash>_initial_schema.py` lives in git. Future devs running `alembic upgrade head` reuse it — don't regenerate it after the first commit.
- **`DATABASE_URL` precedence:** if a `.env` file or shell var sets `DATABASE_URL` to something unexpected, both the app and Alembic use it. Make this explicit in the README so a stale env var doesn't silently send dev writes to a different DB.

---

## Future steps (just placeholders for now)

These will get fleshed out as we work through them. Each maps to the implementation order in [Phase 8 of the main PLANNING.md](../PLANNING.md).

### Step 3: Session cookie management + `/api/whoami` + `/embed` route

Add the `tutor_session_id` cookie issuance on first load. Implement `GET /api/whoami` returning `{session_id, email?, conversation_id?}`. Add `GET /embed?course=&exercise=&tutor=` route that serves a placeholder HTML page.

### Step 4: Tutor bridge

Add `main_ui/services/tutor_bridge.py` that wraps `tutor.run_tutor.create_tutor_graph`. No HTTP route yet — just confirm we can build a tutor graph and get a reply programmatically from `main_ui/`.

### Step 5: `/api/chat` text-only

Implement `POST /api/chat` accepting `{text}`. Creates the conversation row on first message, persists student + tutor messages, returns `{tutor_reply, conversation_id, message_count}`. No images yet.

### Step 6: Frontend chat UI

Build `main_ui/templates/embed.html` + `main_ui/static/js/chat.js` + `main_ui/static/css/chat.css`. Render messages, send via fetch, basic styling. Vanilla JS only.

### Step 7: Email modal

Frontend counts user messages; after the 3rd one, show a modal asking for email. `POST /api/email` validates `@`+`.`, stores in DB, sets `tutor_email` cookie, backfills past anonymous conversations with the same `session_id`.

### Step 8: Conversation history

`GET /api/history` returns past conversations for the current email. `GET /api/conversation/<id>` returns full message log. Add collapsed sidebar UI in `embed.html`.

### Step 9: Image uploads

Switch `/api/chat` to `multipart/form-data`. Save uploads under `main_ui/uploads/`, record in `uploaded_images` table. Build multimodal HumanMessage via `utils/figures.py`. Forward to tutor. **Depends on Phase 6** of the main PLANNING.md being implemented.

### Step 10: Test iframe page

Build `main_ui/test_host.html` — a plain HTML page with multiple iframes at different widths pointing at different course/exercise combos. Local dev verification of the embed UX.

### Step 11: Tests + README + documentation

`main_ui/tests/test_routes.py` and `test_models.py`. Flesh out `main_ui/README.md` with the full local dev workflow. Document env vars, migrations, and the `test_host.html` workflow.
