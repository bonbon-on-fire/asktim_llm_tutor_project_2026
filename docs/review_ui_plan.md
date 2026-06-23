# Plan: `review_ui` — read-only conversation review for AskTIM

> Status: **plan / not yet built.** Action item from the 06/16 meeting:
> "Build a small interface for reviewing real AskTIM conversation data."

## Goal

A read-only mirror of the live chat UI for browsing **all** real conversations
stored in a Railway Postgres. One codebase, deployed as **two Railway services**:

- **Sandbox review** → the `test_ui` Sandbox DB (`Postgres-_lPx`).
- **Normal review** → the `main_ui` production DB (the Postgres `humanities-main`
  references).

It looks like the real chat site (the sidebar + transcript view), but with the
composer and action buttons removed, an all-students conversation list, and a
per-deployment title + color theme so the two are impossible to confuse.

## Decisions locked

- **Identity = email.** There is no "student ID" column in either schema; the
  only identity carrier is `email` (nullable) plus an opaque `session_id`. The
  review UI groups/sorts by email and shows it above each conversation row;
  anonymous sessions (no email) fall back to a muted `Anonymous` / short
  `session_id`.
- **One app, deployed twice.** Single codebase; two Railway services differing
  only by env vars (DB URL, title, theme).
- **Differentiated by title + color** per deployment (see Theming).

## Architecture note that shapes everything

The two DBs have **different schemas**: `test_ui.conversations` has extra columns
(`syllabus_enabled`, `custom_*`, `context_mode`) that `main_ui.conversations`
lacks. So the review app **must not** import `test_ui.db.models` (selecting those
columns would crash against main_ui's DB). It defines its **own minimal,
read-only model** over only the columns common to both:

`id, session_id, email, course, exercise_number, tutor_prompt, started_at,
last_active_at` + `messages` + `uploaded_images`.

One model → works against both databases unchanged.

## Connecting to the Railway DB

Same pattern the live apps already use: read a connection string and open a
SQLAlchemy engine (cf. `test_ui/config.py`). The review app issues **read-only**
queries against the same DB.

**On Railway** (no secrets copied around):

1. Add a **new service** in the `tutors (UW, humanities)` project from this repo.
2. Give it a **reference variable** to share Postgres over the private network:
   `REVIEW_DATABASE_URL = ${{Postgres-_lPx.DATABASE_URL}}` (sandbox) /
   the main Postgres reference (normal).
3. Service boots, reads the URL, queries. No new schema, no `create_all`.

**Local run against prod** (quick review without deploying): use the **public**
URL — `Postgres-_lPx → Variables → DATABASE_PUBLIC_URL` (the `...proxy.rlwy.net`
host). The internal `*.railway.internal` host only resolves inside Railway.

## Repo structure (new top-level package)

```
review_ui/
  __init__.py
  __main__.py
  run_app.py            # Flask app factory; read-only engine from REVIEW_DATABASE_URL
  config.py             # REVIEW_DATABASE_URL, REVIEW_TITLE, REVIEW_THEME/ACCENT, REVIEW_PASSWORD, port
  auth.py               # shared-password gate (login form + session check)
  db/
    models.py           # minimal read-only models (common columns only)
    session.py          # engine + Session (echo off, NO create_all)
  services/
    conversations.py    # list_all_conversations(), get_conversation(), get_image()
  routes/
    review.py           # endpoints below
  static/               # adapted chat.css (themed via CSS vars) + trimmed chat.js
  templates/
    index.html          # adapted from test_ui shell; injects title + theme
    login.html
README.md
```

## Backend endpoints (all read-only, all behind auth)

- `GET /` → app shell (redirect to `/login` if not authed).
- `GET /login`, `POST /login` → shared-password gate; sets a signed session cookie.
- `GET /api/conversations` → **the new piece.** Lists *all* conversations (no
  email scoping, unlike the live email-scoped history). Per row: `id, email,
  course, exercise_number, started_at, last_active_at, message_count`. Supports
  `?sort=date|student` and pagination (`?limit=&offset=`).
- `GET /api/conversation/<uuid>` → full transcript (mirrors the live detail
  endpoint, **without** the ownership check — review sees everything).
- `GET /api/image/<int>` → serve uploaded image bytes (ownership check dropped).

## Frontend (reuse the chat UI, stripped)

Start from `test_ui` templates/JS so it looks identical, then:

- **Remove** the composer ("Ask anything"), **Edit context**, **New chat**.
- **Header + tab title** from `REVIEW_TITLE`.
- **Sidebar list** driven by `/api/conversations`:
  - Sort by **date** (default) and by **student (email)**.
  - Each item shows the **email on a line above** the existing
    `Exercise 1 · Jun 15 · N messages` line; muted `Anonymous` when null.
  - When sorted by student, group rows under each email header.
- **Clicking** a row loads the read-only transcript (reuse the existing message
  renderer: tutor pedagogical-reasoning + inline images).

## Theming + titles (per deployment)

One codebase, re-skinned via env. `index.html` injects a theme onto `:root` as a
CSS custom property; the adapted `chat.css` uses `var(--accent)` for the header
bar, sidebar highlights, links, and selected-row state.

| Var | Sandbox service | Normal service |
| --- | --- | --- |
| `REVIEW_DATABASE_URL` | `${{Postgres-_lPx.DATABASE_URL}}` | main Postgres reference |
| `REVIEW_TITLE` | `AskTIM · Sandbox Database` | `AskTIM · Database` (no "Sandbox") |
| `REVIEW_THEME` | `sandbox` (amber/orange accent) | `production` (blue accent) |
| `REVIEW_ACCENT` (optional) | raw-hex override | raw-hex override |
| `REVIEW_PASSWORD` | shared secret | shared secret |
| `REVIEW_SECRET_KEY` | session signing | session signing |

`REVIEW_THEME` maps to a small built-in palette (named presets); `REVIEW_ACCENT`
optionally overrides with raw hex. Defaults: **sandbox = amber/orange** ("test
data"), **production = blue** ("real student data, handle with care").

> Exact titles + hex values to be confirmed before building the CSS.

## Railway deployment

- New `Dockerfile_review` (copy of `Dockerfile_test`): `COPY review_ui/` +
  `utils/`; **no** `tutor/`, `rag/`, or `curriculum/` (review doesn't run the
  tutor). gunicorn target `review_ui.run_app:app`.
- New `scripts/railway-entrypoint-review.sh`: normalize the Postgres URL to
  `postgresql+psycopg://` (same psycopg3 gotcha the test entrypoint handles),
  **skip** schema creation, start gunicorn.
- Two services, each with the Dockerfile + its env vars + a generated domain.

## Safety (non-negotiable)

- **No writes**: only SELECTs; never `create_all`. Prefer a read-only Postgres
  role for defense-in-depth.
- **Auth gate** on every route — it exposes all students' messages and uploaded
  images, which the live apps deliberately wall off by session/email.
- Treat it as student PII (emails + conversation content); keep it off public
  discovery.

## Open items to confirm before coding

- **Normal-site title** wording (`AskTIM · Database`? `AskTIM Review`?).
- **Colors** — amber (sandbox) / blue (production) defaults, or specific brand hex?
- **Auth** — single shared password enough, or per-reviewer logins / SSO?
- **Search/filter** — beyond sort-by-date/student, want filters (course,
  exercise, date range, full-text message search)? Add now vs. later.

---

## Implementation checklist

### Phase 0 — Confirm spec
- [ ] Confirm normal-site title wording
- [ ] Confirm color palette (sandbox amber / production blue, or brand hex)
- [ ] Confirm auth model (shared password vs per-user)
- [ ] Decide search/filter scope for v1

### Phase 1 — Skeleton + DB connectivity
- [ ] Create `review_ui/` package (`__init__`, `__main__`, `run_app` factory)
- [ ] `config.py` reading `REVIEW_DATABASE_URL`, `REVIEW_TITLE`, `REVIEW_THEME`, `REVIEW_ACCENT`, `REVIEW_PASSWORD`, `REVIEW_SECRET_KEY`, `PORT`
- [ ] `db/models.py` — minimal read-only models (common columns only)
- [ ] `db/session.py` — engine + Session, echo off, **no `create_all`**
- [ ] `services/conversations.py` — `list_all_conversations()`, `get_conversation()`, `get_image()`
- [ ] Smoke test locally against prod via `DATABASE_PUBLIC_URL` (counts + one transcript)

### Phase 2 — Endpoints
- [ ] `GET /api/conversations` (all convos, `?sort=date|student`, pagination, `message_count`)
- [ ] `GET /api/conversation/<uuid>` (full transcript, no ownership check)
- [ ] `GET /api/image/<int>` (serve bytes, no ownership check)
- [ ] Bare HTML list to prove end-to-end before styling

### Phase 3 — Frontend (reuse + strip)
- [ ] Port chat templates/CSS/JS into `review_ui/`
- [ ] Remove composer, Edit context, New chat
- [ ] Sidebar from `/api/conversations`; email line above the `Exercise · date · N msgs` line
- [ ] Sort toggle: date / student (grouped by email)
- [ ] Anonymous fallback for null email
- [ ] Transcript pane reuses message renderer (reasoning + inline images)

### Phase 4 — Theming + title
- [ ] Inject `REVIEW_TITLE` into header + `<title>`
- [ ] CSS custom property `--accent` driven by `REVIEW_THEME`/`REVIEW_ACCENT`
- [ ] Named presets: `sandbox` (amber), `production` (blue)

### Phase 5 — Auth
- [ ] `auth.py` shared-password gate + signed session cookie
- [ ] Guard all routes; `/login` + `/login` POST + logout

### Phase 6 — Deploy
- [ ] `Dockerfile_review` + `scripts/railway-entrypoint-review.sh`
- [ ] Deploy **sandbox** service (DB `Postgres-_lPx`), verify, generate domain
- [ ] Clone service for **normal** DB; set its env vars; verify, generate domain
- [ ] Confirm read-only (no schema writes), auth required, both themes correct

### Phase 7 — Docs
- [ ] `review_ui/README.md` (run locally, env vars, deploy notes)
- [ ] Link from root `README.md` / `PLANNING.md`
