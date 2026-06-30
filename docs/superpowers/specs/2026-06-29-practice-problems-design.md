# Practice Problems as a Distinct Content Kind — Design

Date: 2026-06-29
Status: Draft for review

## Problem

The curriculum supports one kind of selectable assignment per course: exercises,
stored as `curriculum/<course>/exercises/exercise_<NN>.txt` and discovered/resolved
through `utils/curriculum.py`. Some courses (e.g. MITx CTL.SC2x Supply Chain
Design) also ship **practice problems** — ungraded problem sets that are
pedagogically distinct from the graded exercises but should be selectable in the
sandbox the same way exercises are, and fed to the tutor identically.

We want to add practice problems as a **distinct, labeled category** in the
Create-context wizard: they function like exercises (selectable, resolved into
tutor context) but are stored under a different filename prefix and shown as a
separate group, and the chosen kind is persisted per conversation.

This is a `sandbox_ui`-only + shared-resolver change. No change to batch runners'
behavior for existing exercises.

## Non-goals (YAGNI)

- **No figure support for practice problems in v1.** The SC2x practice sets are
  text/tables only. A future `practice_<NN>_*.png` convention in
  `utils/figures.py` can be added if needed.
- **No generic N-kind system.** Exactly two kinds: `exercise` (default) and
  `practice`. We are not generalizing the resolver to arbitrary prefixes.
- **No change to the `/embed` query-param flow** beyond what is required; embed
  continues to serve exercises. (Practice via embed can follow later.)

## Disk convention

Practice problems live alongside exercises in the same folder, with a parallel
prefix:

```
curriculum/<course>/exercises/
  exercise_01.txt      # graded exercises (unchanged)
  practice_01.txt      # practice problems (new)
  practice_02.txt
```

Strict naming: `practice_(\d{2})\.txt`, mirroring the existing
`exercise_(\d{2})\.txt`.

## Design

The selection model becomes a `(kind, number)` pair, where `kind ∈ {exercise,
practice}` and `number` is the existing zero-padded 2-digit string. `exercise`
is the default everywhere, so existing behavior and existing stored
conversations are unaffected.

### 1. Resolver — `utils/curriculum.py`

Refactor the exercise helpers so their bodies share a private implementation
parameterized by prefix, then expose a parallel practice set:

- Private: `_discover(folder, prefix)`, `_item_path(course, prefix, number, root)`,
  `_item_exists(...)`, `_read_item(...)`.
- Public (unchanged signatures/behavior): `discover_exercises`, `exercise_path`,
  `exercise_exists`, `read_exercise`.
- Public (new): `discover_practice`, `practice_path`, `practice_exists`,
  `read_practice`.

The public exercise functions must keep identical behavior (existing call sites
untouched). Per-prefix strict regex.

### 2. Persistence — `sandbox_ui/db/models.py` + `run_app` reconcile

Add a nullable column to `Conversation`:

```python
exercise_kind: Mapped[str] = mapped_column(Text, nullable=False, default="exercise")
```

`create_all` cannot add a column to a pre-existing table, so
`_reconcile_columns()` in `run_app` adds it (same mechanism already used for
`course_enabled` and `syllabus_enabled`). Legacy rows read back `NULL` and are
treated as `"exercise"` on read (`c.exercise_kind or "exercise"`), so reopening
an old chat replays it as an exercise exactly as today.

### 3. Options API — `sandbox_ui/routes/_validation.py`

- `context_options()` adds `practice: ["01", ...]` per course, via a new
  `list_practice(course)` -> `discover_practice`.
- Add `validate_practice(course, number)` and `load_practice_text(course, number)`
  mirroring `validate_exercise` / `load_exercise_text`.
- Add a small dispatcher used by the route: given `(kind, number)`, validate and
  resolve against the right prefix.

Resulting course shape:

```json
{"slug": ..., "name": ..., "exercises": ["01", ...], "practice": ["01", ...],
 "has_syllabus": bool, "has_rag": bool}
```

### 4. Wizard — `sandbox_ui/static/js/chat.js`

The exercise step's `<select>` renders two labeled groups using `<optgroup>`:

- **Exercises** — `exercise:<NN>` options (from `course.exercises`)
- **Practice problems** — `practice:<NN>` options (from `course.practice`)
- **Create custom exercise** — unchanged sentinel (`CUSTOM`); custom is always
  treated as kind `exercise`.

Option values encode kind, e.g. `exercise:01` / `practice:03`. The course step's
existing dependency (exercise list keyed off `courseBySlug(cd.existing)`) is
preserved. The create-draft and `config` carry both `exercise` (number) and
`exerciseKind`. When the course has no `practice` entries, the Practice
`<optgroup>` is omitted (mirrors how the syllabus/RAG steps hide unavailable
options).

The exercise-preview behavior (textarea) uses the kind to fetch the right text
for the preview where applicable.

### 5. Request/persistence — `sandbox_ui/routes/chat.py`, `services/conversation.py`

- Parse `exercise_kind` from the request body (`src.get("exercise_kind")`),
  defaulting to `"exercise"`; coerce/validate to the allowed set.
- `find_or_create_conversation(...)` gains an `exercise_kind="exercise"` param,
  stored on the new row.
- On the streaming path, read back `stream_exercise_kind = convo.exercise_kind or
  "exercise"` and pass it to the tutor call (mirrors `stream_course_enabled`).
- `_summarize_conversation` includes `"exercise_kind"` so history replays the
  same kind.

### 6. Tutor resolution — `sandbox_ui/services/tutor_bridge.py`

`build_assignment_text` resolves the built-in exercise file via
`exercise_path(course, exercise)` ([current line ~160]). Thread an
`exercise_kind: str = "exercise"` parameter through the same call chain that
`include_course` / `include_syllabus` already flow through
(`build_assignment_text` → `_resolve_system_prompt` → `_get_or_build_graph` /
`_get_or_build_stream_context` → `get_tutor_reply` / `stream_tutor_reply`).
When `exercise_kind == "practice"`, resolve `practice_path(course, exercise)`
instead. A custom `exercise_text` override still wins and is unaffected by kind.

Both prompt-cache keys (`_graph_cache`, `_stream_cache`) gain `exercise_kind` so
practice and exercise prompts for the same number don't collide.

## Data flow (after change)

```
disk: exercises/{exercise,practice}_<NN>.txt
  -> discover_exercises / discover_practice            (utils/curriculum.py)
  -> context_options(): course.exercises + course.practice   (_validation.py)
  -> wizard exercise step: two <optgroup>s, value "kind:NN"   (chat.js)
  -> POST /api/chat: exercise=<NN>, exercise_kind=<kind>      (chat.py)
  -> Conversation(exercise_number=NN, exercise_kind=kind)     (models.py / conversation.py)
  -> tutor call: include exercise_kind -> resolve {exercise,practice}_path  (tutor_bridge.py)
```

## Backward compatibility

- Existing `exercise_*.txt` files, existing wizard exercise selections, and
  existing stored conversations behave identically (`exercise_kind` defaults to
  and reads back as `"exercise"`).
- Courses with no `practice_*.txt` files simply expose an empty `practice` list
  and the wizard omits the Practice group.
- Batch runners and `utils.curriculum` exercise APIs are unchanged.

## Testing

- `utils/curriculum.py`: unit tests for `discover_practice` (only matches
  `practice_<NN>.txt`, ignores `exercise_*`, sorted), `practice_path`,
  `practice_exists`, `read_practice`; and a regression test that the exercise
  functions still ignore `practice_*`.
- `_validation.py`: `context_options()` includes `practice`; validate/load
  dispatch by kind.
- Manual wizard walkthrough: (a) select a practice problem -> new conversation
  resolves the `practice_<NN>.txt` text into tutor context; (b) select an
  exercise -> unchanged; (c) a course with no practice files shows no Practice
  group; (d) reopen a pre-change conversation -> still resolves as exercise.

## Affected files

- `utils/curriculum.py` (resolver: shared helper + practice functions)
- `sandbox_ui/db/models.py` (`exercise_kind` column)
- `sandbox_ui/run_app` `_reconcile_columns()` (backfill column)
- `sandbox_ui/routes/_validation.py` (options + validate/load dispatch)
- `sandbox_ui/routes/chat.py` (parse/persist/pass kind)
- `sandbox_ui/services/conversation.py` (param + summary)
- `sandbox_ui/services/tutor_bridge.py` (thread kind, resolve practice, cache keys)
- `sandbox_ui/static/js/chat.js` (two optgroups, carry kind)
- `sandbox_ui/README.md` (document practice problems)
- Tests under the repo's test layout for `utils/curriculum.py` and `_validation.py`
