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

## Future steps (just placeholders for now)

These will get fleshed out as we work through them. Each maps to the implementation order in [Phase 8 of the main PLANNING.md](../PLANNING.md).

### Step 2: Database schema + Alembic migrations + SQLAlchemy models

Add `main_ui/db/` with SQLAlchemy models for `Conversation`, `Message`, `UploadedImage`. Set up Alembic migrations. Get `alembic upgrade head` working against both SQLite (default) and Postgres (via Docker).

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
