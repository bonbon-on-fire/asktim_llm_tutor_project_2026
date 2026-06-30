# Practice Problems Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `practice_<NN>.txt` practice problems to the curriculum as a distinct, separately-labeled, selectable category in the sandbox_ui Create-context wizard, persisted per conversation and resolved into tutor context exactly like exercises.

**Architecture:** A selection becomes a `(kind, number)` pair where `kind ∈ {exercise, practice}` and `exercise` is the default everywhere. The shared resolver (`utils/curriculum.py`) gains a parallel practice API; a new nullable `exercise_kind` column on `Conversation` persists the kind; the kind threads through the route → conversation → tutor_bridge the same way `include_course`/`include_syllabus` already do; the wizard renders two `<optgroup>`s.

**Tech Stack:** Python 3, Flask, SQLAlchemy (sandbox_ui), vanilla JS (chat.js). Tests in utils/ are **standalone** (no pytest) — run with `python -m utils.<module>`.

## Global Constraints

- Practice files live at `curriculum/<course>/exercises/practice_<NN>.txt`; strict name regex `^practice_(\d{2})\.txt$` (exactly two digits), mirroring exercises.
- `exercise_kind` allowed values: `"exercise"` (default) and `"practice"`. Any custom/unknown value is treated as `"exercise"`.
- Existing exercise behavior, existing wizard exercise selections, and existing stored conversations MUST behave identically (default + legacy `NULL` → `"exercise"`).
- No figure support for practice problems in v1.
- sandbox_ui has no pytest harness; Python web-layer functions are tested standalone (import directly, no Flask app) or verified manually as noted.
- `_reconcile_columns()` in `sandbox_ui/run_app.py` auto-adds any model column missing from the live table (as nullable). Declaring the column on the model is sufficient — do NOT hand-edit run_app.

---

### Task 1: Resolver — practice API in `utils/curriculum.py`

**Files:**
- Modify: `utils/curriculum.py`
- Test: `utils/test_curriculum.py` (create)

**Interfaces:**
- Produces:
  - `discover_practice(course: str, curriculum_root=None) -> list[str]` — sorted 2-digit numbers for `practice_<NN>.txt`.
  - `practice_path(course: str, practice_number: str, curriculum_root=None) -> Path`
  - `practice_exists(course: str, practice_number: str, curriculum_root=None) -> bool`
  - `read_practice(course: str, practice_number: str, curriculum_root=None) -> str`
  - Existing `discover_exercises` / `exercise_path` / `exercise_exists` / `read_exercise` keep identical signatures and behavior.

- [ ] **Step 1: Write the failing test**

Create `utils/test_curriculum.py`:

```python
"""Standalone tests for utils.curriculum (no pytest dependency).

Run with:
    python -m utils.test_curriculum
"""

from __future__ import annotations

from pathlib import Path
import tempfile

from utils.curriculum import (
    discover_exercises,
    discover_practice,
    practice_exists,
    practice_path,
    read_practice,
)

_PASSED = 0
_FAILED = 0


def _check(name: str, condition: bool, detail: str = "") -> None:
    global _PASSED, _FAILED
    if condition:
        _PASSED += 1
        print(f"  PASS  {name}")
    else:
        _FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def test_discover_practice_filters_and_sorts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        exdir = root / "demo" / "exercises"
        exdir.mkdir(parents=True)
        (exdir / "practice_02.txt").write_text("p2", encoding="utf-8")
        (exdir / "practice_01.txt").write_text("p1", encoding="utf-8")
        (exdir / "exercise_01.txt").write_text("e1", encoding="utf-8")
        (exdir / "practice_1_bad.txt").write_text("x", encoding="utf-8")
        (exdir / "practice_01.md").write_text("x", encoding="utf-8")

        prac = discover_practice("demo", curriculum_root=root)
        _check("practice sorted + filtered", prac == ["01", "02"], f"got {prac}")
        ex = discover_exercises("demo", curriculum_root=root)
        _check("exercises ignore practice_*", ex == ["01"], f"got {ex}")


def test_practice_path_exists_and_read() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        exdir = root / "demo" / "exercises"
        exdir.mkdir(parents=True)
        (exdir / "practice_03.txt").write_text("hello practice", encoding="utf-8")

        p = practice_path("demo", "03", curriculum_root=root)
        _check("practice_path points at file", p.name == "practice_03.txt", f"got {p.name}")
        _check("practice_exists true", practice_exists("demo", "03", curriculum_root=root))
        _check("practice_exists false for missing", not practice_exists("demo", "99", curriculum_root=root))
        _check("read_practice returns text", read_practice("demo", "03", curriculum_root=root) == "hello practice")
        _check("read_practice missing -> ''", read_practice("demo", "99", curriculum_root=root) == "")


def main() -> int:
    tests = [
        test_discover_practice_filters_and_sorts,
        test_practice_path_exists_and_read,
    ]
    for t in tests:
        print(t.__name__)
        t()
    print(f"\n{_PASSED} passed, {_FAILED} failed")
    return 1 if _FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m utils.test_curriculum`
Expected: ImportError (`cannot import name 'discover_practice'`) or FAIL.

- [ ] **Step 3: Add the practice API to `utils/curriculum.py`**

Add the practice regex next to the existing exercise one (after line 19):

```python
# practice_<NN>.txt — exactly two digits (parallel to exercises).
_PRACTICE_NAME_RE = re.compile(r"^practice_(\d{2})\.txt$")
```

Add these functions (place after `read_exercise`, before `discover_exercises`):

```python
def practice_path(
    course: str,
    practice_number: str,
    curriculum_root: Path | str | None = None,
) -> Path:
    """Return the path to a course's practice-problem file (existence not guaranteed)."""
    return exercises_dir(course, curriculum_root) / f"practice_{practice_number}.txt"


def practice_exists(
    course: str,
    practice_number: str,
    curriculum_root: Path | str | None = None,
) -> bool:
    """True when the practice-problem file exists on disk."""
    if not course or not practice_number:
        return False
    return practice_path(course, practice_number, curriculum_root).is_file()


def read_practice(
    course: str,
    practice_number: str,
    curriculum_root: Path | str | None = None,
) -> str:
    """Read a practice-problem file's text, or ``""`` when absent."""
    path = practice_path(course, practice_number, curriculum_root)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def discover_practice(
    course: str,
    curriculum_root: Path | str | None = None,
) -> list[str]:
    """Return sorted zero-padded 2-digit practice-problem numbers for a course."""
    folder = exercises_dir(course, curriculum_root)
    if not folder.is_dir():
        return []
    nums: list[str] = []
    for path in folder.glob("practice_*.txt"):
        m = _PRACTICE_NAME_RE.match(path.name)
        if m:
            nums.append(m.group(1))
    return sorted(nums)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m utils.test_curriculum`
Expected: `4 passed, 0 failed` (PASS lines for all checks).

Also run the existing figures test to confirm no regression in shared helpers:
Run: `python -m utils.test_figures`
Expected: existing `N passed, 0 failed`.

- [ ] **Step 5: Export new names from `utils/__init__.py`**

In `utils/__init__.py`, add `discover_practice`, `practice_exists`, `practice_path`, `read_practice` to both the import block from `.curriculum` and the `__all__` list (alphabetical, next to the exercise entries).

- [ ] **Step 6: Verify import surface**

Run: `python -c "from utils import discover_practice, practice_path, practice_exists, read_practice; print('ok')"`
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add utils/curriculum.py utils/test_curriculum.py utils/__init__.py
git commit -m "feat(curriculum): add practice_<NN> resolver API"
```

---

### Task 2: Tutor resolution — thread `exercise_kind` through `tutor_bridge.py`

**Files:**
- Modify: `sandbox_ui/services/tutor_bridge.py`
- Test: `sandbox_ui/services/test_tutor_bridge_practice.py` (create)

**Interfaces:**
- Consumes: `practice_path` from Task 1.
- Produces: `build_assignment_text(..., exercise_kind: str = "exercise")` and the same new keyword on `_resolve_system_prompt`, `_get_or_build_graph`, `_get_or_build_stream_context`, `get_tutor_reply`, `stream_tutor_reply`. Cache keys include `exercise_kind`.

- [ ] **Step 1: Write the failing test**

Create `sandbox_ui/services/test_tutor_bridge_practice.py`:

```python
"""Standalone test: build_assignment_text resolves practice files by kind.

Run with:
    python -m sandbox_ui.services.test_tutor_bridge_practice
"""

from __future__ import annotations

from pathlib import Path

from sandbox_ui.services.tutor_bridge import build_assignment_text

_REPO = Path(__file__).resolve().parents[2]
_CURRICULUM = _REPO / "curriculum"

_PASSED = 0
_FAILED = 0


def _check(name, cond, detail=""):
    global _PASSED, _FAILED
    if cond:
        _PASSED += 1
        print(f"  PASS  {name}")
    else:
        _FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    # Use a temp practice file in a real-shaped course dir.
    import tempfile, shutil
    with tempfile.TemporaryDirectory() as tmp:
        course = "tmp_course_practice"
        exdir = _CURRICULUM / course / "exercises"
        exdir.mkdir(parents=True, exist_ok=True)
        (exdir / "exercise_01.txt").write_text("EXERCISE ONE BODY", encoding="utf-8")
        (exdir / "practice_01.txt").write_text("PRACTICE ONE BODY", encoding="utf-8")
        try:
            ex_text = build_assignment_text(course, "01", exercise_kind="exercise")
            pr_text = build_assignment_text(course, "01", exercise_kind="practice")
            _check("exercise kind resolves exercise file", "EXERCISE ONE BODY" in ex_text, ex_text)
            _check("practice kind resolves practice file", "PRACTICE ONE BODY" in pr_text, pr_text)
            _check("default kind is exercise", "EXERCISE ONE BODY" in build_assignment_text(course, "01"))
        finally:
            shutil.rmtree(_CURRICULUM / course, ignore_errors=True)
    print(f"\n{_PASSED} passed, {_FAILED} failed")
    return 1 if _FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m sandbox_ui.services.test_tutor_bridge_practice`
Expected: FAIL/TypeError — `build_assignment_text() got an unexpected keyword argument 'exercise_kind'`.

- [ ] **Step 3: Add the import**

In `sandbox_ui/services/tutor_bridge.py`, line 31 currently reads `from utils.curriculum import exercise_path`. Change it to:

```python
from utils.curriculum import exercise_path, practice_path
```

- [ ] **Step 4: Add the `exercise_kind` param + resolution in `build_assignment_text`**

In the signature of `build_assignment_text` (around lines 80-90), add after `exercise: str,` and the `*,` marker, alongside `include_course`:

```python
    exercise_kind: str = "exercise",
```

Replace the built-in exercise resolution block (currently around lines 157-161):

```python
    if exercise_text is not None:
        resolved_exercise = exercise_text.strip()
    else:
        resolved_exercise = exercise_path(course, exercise).read_text(encoding="utf-8").strip()
    parts.append("Exercise:\n" + resolved_exercise)
```

with:

```python
    if exercise_text is not None:
        resolved_exercise = exercise_text.strip()
    else:
        _path = (
            practice_path(course, exercise)
            if exercise_kind == "practice"
            else exercise_path(course, exercise)
        )
        resolved_exercise = _path.read_text(encoding="utf-8").strip()
    parts.append("Exercise:\n" + resolved_exercise)
```

- [ ] **Step 5: Thread `exercise_kind` through the call chain + cache keys**

For each of these functions add `exercise_kind: str = "exercise"` to the keyword-only params and pass `exercise_kind=exercise_kind` down to the function it calls:

- `_resolve_system_prompt` (~line 205) → passes to `build_assignment_text`.
- `_get_or_build_graph` (~line 232) → passes to `_resolve_system_prompt`; and add `exercise_kind` to its `key` tuple.
- `_get_or_build_stream_context` (~line 270) → passes to `_resolve_system_prompt`; add `exercise_kind` to its `key` tuple.
- `get_tutor_reply` (~line 387) → passes to `_get_or_build_graph`.
- `stream_tutor_reply` (~line 461) → passes to `_get_or_build_stream_context`.

Cache key change (both caches): the tuple currently is
`(tutor, course, exercise, include_course, include_syllabus, context_mode)`.
Change both to
`(tutor, course, exercise, include_course, include_syllabus, exercise_kind, context_mode)`
and update the two cache type annotations near the top of the file
(`_graph_cache` / `_stream_cache`) to add one more `str` element.

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m sandbox_ui.services.test_tutor_bridge_practice`
Expected: `3 passed, 0 failed`.

- [ ] **Step 7: Commit**

```bash
git add sandbox_ui/services/tutor_bridge.py sandbox_ui/services/test_tutor_bridge_practice.py
git commit -m "feat(tutor_bridge): resolve practice files via exercise_kind"
```

---

### Task 3: Persistence — `exercise_kind` column + conversation plumbing

**Files:**
- Modify: `sandbox_ui/db/models.py`
- Modify: `sandbox_ui/services/conversation.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `Conversation.exercise_kind` (str, default `"exercise"`); `find_or_create_conversation(..., exercise_kind="exercise")`; `_summarize_conversation` returns `"exercise_kind"`.

- [ ] **Step 1: Add the column to `Conversation`**

In `sandbox_ui/db/models.py`, immediately after the `exercise_number` column (line 48), add:

```python
    # sandbox_ui-only: which content kind this conversation's exercise_number
    # refers to — "exercise" (graded, default) or "practice". create_all can't
    # add this to a pre-existing table, but _reconcile_columns() in run_app does.
    # Legacy rows read back NULL and are treated as "exercise" on read.
    exercise_kind: Mapped[str] = mapped_column(
        Text, nullable=False, default="exercise"
    )
```

(`Text` and `mapped_column` are already imported in this file.)

- [ ] **Step 2: Add the param to `find_or_create_conversation`**

In `sandbox_ui/services/conversation.py`, add `exercise_kind: str = "exercise",` to the keyword-only params (after `exercise_number: str,`, near line 30), and add `exercise_kind=exercise_kind,` to the `Conversation(...)` constructor (after `exercise_number=exercise_number,`, near line 64).

- [ ] **Step 3: Add `exercise_kind` to the conversation summary**

In `_summarize_conversation` (around line 300), after the `"exercise_number": c.exercise_number,` entry, add:

```python
        "exercise_kind": c.exercise_kind or "exercise",
```

- [ ] **Step 4: Verify the model imports and column default**

Run:
```bash
python -c "from sandbox_ui.db.models import Conversation; c=Conversation(session_id='s', course='x', exercise_number='01', tutor_prompt='tutor_05'); print(c.exercise_kind)"
```
Expected: prints `None` at construction time (SQLAlchemy defaults apply on flush) — no AttributeError. This confirms the attribute exists.

- [ ] **Step 5: Commit**

```bash
git add sandbox_ui/db/models.py sandbox_ui/services/conversation.py
git commit -m "feat(db): add Conversation.exercise_kind column + plumbing"
```

---

### Task 4: Options & validation API — `_validation.py` + `embed.py` preview

**Files:**
- Modify: `sandbox_ui/routes/_validation.py`
- Modify: `sandbox_ui/routes/embed.py`
- Test: `sandbox_ui/routes/test_validation_practice.py` (create)

**Interfaces:**
- Consumes: `discover_practice`, `practice_exists`, `read_practice` from Task 1.
- Produces: `list_practice(course) -> list[str]`; `validate_practice(course, number) -> dict | None`; `load_practice_text(course, number) -> str`; `list_context_options()` courses include `"practice": [...]`; `/api/context/preview?kind=practice` works.

- [ ] **Step 1: Write the failing test**

Create `sandbox_ui/routes/test_validation_practice.py`:

```python
"""Standalone test for practice options/validation in _validation.

Run with:
    python -m sandbox_ui.routes.test_validation_practice
"""

from __future__ import annotations

from pathlib import Path
import tempfile, shutil

from sandbox_ui.routes import _validation as V

_PASSED = 0
_FAILED = 0


def _check(name, cond, detail=""):
    global _PASSED, _FAILED
    if cond:
        _PASSED += 1
        print(f"  PASS  {name}")
    else:
        _FAILED += 1
        print(f"  FAIL  {name}  {detail}")


def main() -> int:
    course = "tmp_course_validate_practice"
    exdir = V._CURRICULUM_DIR / course / "exercises"
    exdir.mkdir(parents=True, exist_ok=True)
    (exdir / "practice_01.txt").write_text("PRACTICE BODY", encoding="utf-8")
    try:
        _check("list_practice finds it", V.list_practice(course) == ["01"], V.list_practice(course))
        _check("validate_practice ok", V.validate_practice(course, "01") is None)
        _check("validate_practice missing", V.validate_practice(course, "99") is not None)
        _check("validate_practice bad format", V.validate_practice(course, "1") is not None)
        _check("load_practice_text", V.load_practice_text(course, "01") == "PRACTICE BODY")
        opts = V.list_context_options()
        entry = next((c for c in opts["courses"] if c["slug"] == course), None)
        _check("context_options exposes practice", entry is not None and entry.get("practice") == ["01"], entry)
    finally:
        shutil.rmtree(V._CURRICULUM_DIR / course, ignore_errors=True)
    print(f"\n{_PASSED} passed, {_FAILED} failed")
    return 1 if _FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m sandbox_ui.routes.test_validation_practice`
Expected: AttributeError (`module ... has no attribute 'list_practice'`).

- [ ] **Step 3: Add practice imports + functions to `_validation.py`**

Extend the curriculum imports (lines 13-15) to add:

```python
from utils.curriculum import discover_practice as _discover_practice
from utils.curriculum import practice_exists as _practice_exists
from utils.curriculum import read_practice as _read_practice
```

Add these functions (place `validate_practice` after `validate_exercise`, and the loaders/listers near their exercise counterparts):

```python
def validate_practice(course, practice) -> dict | None:
    if not practice:
        return _err("practice", practice, "missing")
    if not (isinstance(practice, str) and len(practice) == 2 and practice.isdigit()):
        return _err(
            "practice", practice, "must be a zero-padded 2-digit number (e.g. 04)"
        )
    if not _practice_exists(course, practice):
        return _err(
            "practice", practice,
            f"no practice_{practice}.txt under curriculum/{course}/exercises/",
        )
    return None


def load_practice_text(course, practice) -> str:
    """Raw practice_<NN>.txt for a built-in course/practice problem."""
    if not course or not practice:
        return ""
    return _read_practice(course, practice)


def list_practice(course) -> list[str]:
    """Sorted zero-padded 2-digit practice-problem numbers for a course."""
    if not course:
        return []
    return _discover_practice(course)
```

- [ ] **Step 4: Add `practice` to `list_context_options`**

In the course dict built inside `list_context_options` (lines 161-167), add a line after `"exercises": list_exercises(slug),`:

```python
                "practice": list_practice(slug),
```

Update the docstring shape comment to include `"practice": [...]`.

- [ ] **Step 5: Add a `validate_kind` dispatcher (used by the route in Task 5)**

Append to `_validation.py`:

```python
def validate_selection(course, number, kind) -> dict | None:
    """Validate a (kind, number) assignment selection against the right prefix."""
    if kind == "practice":
        return validate_practice(course, number)
    return validate_exercise(course, number)
```

- [ ] **Step 6: Add `kind=practice` to the preview endpoint**

In `sandbox_ui/routes/embed.py`, import `load_practice_text` and `validate_practice` from `._validation` (add to the existing import block). Then, in `context_preview()` after the `if kind == "exercise":` block (line 83), add:

```python
    if kind == "practice":
        err = validate_course(course) or validate_practice(course, exercise)
        if err:
            return _bad_param(err)
        return jsonify({"text": load_practice_text(course, exercise)})
```

(The wizard sends the practice number in the existing `exercise` query param; see Task 6.)

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m sandbox_ui.routes.test_validation_practice`
Expected: `6 passed, 0 failed`.

- [ ] **Step 8: Commit**

```bash
git add sandbox_ui/routes/_validation.py sandbox_ui/routes/embed.py sandbox_ui/routes/test_validation_practice.py
git commit -m "feat(api): practice options, validation, and preview"
```

---

### Task 5: Chat route — parse, persist, and pass `exercise_kind`

**Files:**
- Modify: `sandbox_ui/routes/chat.py`

**Interfaces:**
- Consumes: `validate_selection` (Task 4), `find_or_create_conversation(exercise_kind=...)` (Task 3), `stream_tutor_reply(exercise_kind=...)` (Task 2).
- Produces: the request's `exercise_kind` field is honored on new conversations and replayed on continuations.

- [ ] **Step 1: Parse `exercise_kind` from the request**

In `sandbox_ui/routes/chat.py`, after the `exercise = src.get("exercise")` line (line 111), add:

```python
    raw_kind = src.get("exercise_kind")
    exercise_kind = "practice" if str(raw_kind).strip().lower() == "practice" else "exercise"
```

- [ ] **Step 2: Validate the selection by kind**

Replace the exercise validation call (line 178) `err = validate_exercise(course, exercise)` with:

```python
            err = validate_selection(course, exercise, exercise_kind)
```

Update the import at the top of `chat.py` to pull `validate_selection` from `._validation` (add it to the existing import list; `validate_exercise` may stay imported or be dropped if unused).

- [ ] **Step 3: Persist the kind on create**

In the `find_or_create_conversation(...)` call (lines 208-223), add after `exercise_number=exercise,`:

```python
            exercise_kind=exercise_kind,
```

- [ ] **Step 4: Read back the kind and pass it to the tutor call**

After `stream_exercise = convo.exercise_number` (line 263), add:

```python
    # Legacy rows predating this column read back NULL; treat as "exercise".
    stream_exercise_kind = convo.exercise_kind or "exercise"
```

In the `stream_kwargs = dict(...)` block (lines 287-301), add after `exercise=stream_exercise,`:

```python
        exercise_kind=stream_exercise_kind,
```

- [ ] **Step 5: Manual verification (no unit harness for the Flask route)**

Run the app and exercise both paths once Task 6 lands; for now confirm the module imports cleanly:

Run: `python -c "import sandbox_ui.routes.chat as c; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add sandbox_ui/routes/chat.py
git commit -m "feat(chat): honor and replay exercise_kind"
```

---

### Task 6: Wizard — two `<optgroup>`s and kind plumbing in `chat.js`

**Files:**
- Modify: `sandbox_ui/static/js/chat.js`

**Interfaces:**
- Consumes: `context.courses[].practice` (Task 4); the route's `exercise_kind` field (Task 5); `/api/context/preview?kind=practice` (Task 4).
- Produces: a Practice-problems group in the exercise step; `config.exerciseKind` carried into the chat payload.

- [ ] **Step 1: Default `config.exerciseKind`**

Near the other config defaults (after line 9), add:

```javascript
  // Which content kind the exercise selection refers to: "exercise" (default)
  // or "practice". Carried with each /api/chat send.
  if (typeof config.exerciseKind === "undefined") config.exerciseKind = "exercise";
```

- [ ] **Step 2: Make `buildSelect` support optgroups**

Replace `buildSelect` (lines 680-692) with a version that accepts either flat options or `{group, options}` entries:

```javascript
  function buildSelect(options, value) {
    const sel = document.createElement("select");
    sel.className = "context-select";
    sel.id = "create-select";
    const addOption = (parent, o) => {
      const opt = document.createElement("option");
      opt.value = o.value;
      opt.textContent = o.label;
      if (o.value === value) opt.selected = true;
      parent.appendChild(opt);
    };
    for (const o of options) {
      if (o.group) {
        if (!o.options.length) continue;
        const og = document.createElement("optgroup");
        og.label = o.group;
        for (const inner of o.options) addOption(og, inner);
        sel.appendChild(og);
      } else {
        addOption(sel, o);
      }
    }
    return sel;
  }
```

- [ ] **Step 3: Encode kind in the exercise step's option values**

In `renderCreateStep`, replace the `else if (step === "exercise")` branch (lines 730-749) with one that builds two groups and a custom option, using `exercise:` / `practice:` value prefixes:

```javascript
    } else if (step === "exercise") {
      const cd = createDraft.course;
      const courseObj = cd.mode === "existing" ? courseBySlug(cd.existing) : null;
      const exs = (courseObj && courseObj.exercises) || [];
      const pracs = (courseObj && courseObj.practice) || [];
      options = [
        {
          group: "Exercises",
          options: exs.map((n) => ({
            value: "exercise:" + n,
            label: "Exercise " + (parseInt(n, 10) || n),
          })),
        },
        {
          group: "Practice problems",
          options: pracs.map((n) => ({
            value: "practice:" + n,
            label: "Practice " + (parseInt(n, 10) || n),
          })),
        },
        { value: CUSTOM, label: "Create custom exercise" },
      ];
      const d = createDraft.exercise;
      if (cd.mode === "custom") {
        currentValue = CUSTOM; // custom course has no built-in exercises
      } else if (d.mode === "custom") {
        currentValue = CUSTOM;
      } else {
        const firstExisting =
          (exs[0] && "exercise:" + exs[0]) ||
          (pracs[0] && "practice:" + pracs[0]) ||
          CUSTOM;
        currentValue =
          d.existing ? d.kind + ":" + d.existing : firstExisting;
      }
      customValue = d.custom;
      placeholder = "Paste or write the exercise…";
    }
```

Note: the existing fallback at lines 781-783 (default to first option when no match) still applies for flat values like `CUSTOM`; the explicit `currentValue` above covers the grouped case.

- [ ] **Step 4: Initialize the exercise draft with a `kind`**

In `openCreateModal`'s `createDraft` initializer (lines 972-978), change the exercise line to:

```javascript
      exercise: { mode: "existing", existing: "", custom: "", kind: "exercise" },
```

- [ ] **Step 5: Parse kind in the step save handler**

In `saveCreateStep` (the generic tail at lines 941-948), the exercise step needs special handling because its values are prefixed. Add a dedicated branch BEFORE the generic `const d = createDraft[step];` block:

```javascript
    if (step === "exercise") {
      const d = createDraft.exercise;
      if (sel.value === CUSTOM) {
        d.mode = "custom";
        d.custom = ta.value;
      } else {
        d.mode = "existing";
        const [kind, num] = sel.value.split(":");
        d.kind = kind === "practice" ? "practice" : "exercise";
        d.existing = num || "";
      }
      return;
    }
```

- [ ] **Step 6: Carry kind into `config` in the finish handler**

In the finish handler (lines 1030-1037), replace the exercise block with:

```javascript
    // A custom course has no built-in exercises, so its exercise is custom too.
    if (c.mode === "custom" || e.mode === "custom") {
      config.exercise = null;
      config.exerciseCustom = e.custom;
      config.exerciseKind = "exercise";
    } else {
      config.exercise = e.existing;
      config.exerciseCustom = null;
      config.exerciseKind = e.kind === "practice" ? "practice" : "exercise";
    }
```

- [ ] **Step 7: Send `exercise_kind` on every chat send**

In the `fields` object (lines 1249-1256), add after `exercise: config.exercise,`:

```javascript
      exercise_kind: config.exerciseKind,
```

- [ ] **Step 8: Fix the preview fetch for practice**

In `fetchPreviewText` (lines 656-669), the exercise branch passes the raw selected value. Update the exercise preview to send the correct kind + bare number. Replace the `else if (stepKey === "exercise")` branch with:

```javascript
    } else if (stepKey === "exercise") {
      const raw = String(value || "");
      const isPractice = raw.startsWith("practice:");
      const num = raw.includes(":") ? raw.split(":")[1] : raw;
      url =
        `/api/context/preview?kind=${isPractice ? "practice" : "exercise"}` +
        `&course=${encodeURIComponent(createDraft.course.existing)}` +
        `&exercise=${encodeURIComponent(num)}`;
    }
```

- [ ] **Step 9: Manual verification**

Start the sandbox app (per repo conventions, e.g. `python -m sandbox_ui.run_app` or the documented run command). In the Create-context wizard:
- For `supply_chain_design`, the Exercise step shows an **Exercises** group (01–03) and, once practice files exist, a **Practice problems** group.
- Selecting a practice problem and finishing starts a chat whose tutor context contains the practice text (verify the tutor responds about the practice scenario).
- Selecting an exercise behaves exactly as before.
- A course with no practice files shows no Practice group.

- [ ] **Step 10: Commit**

```bash
git add sandbox_ui/static/js/chat.js
git commit -m "feat(wizard): practice-problems group + exercise_kind plumbing"
```

---

### Task 7: Docs + full end-to-end verification

**Files:**
- Modify: `sandbox_ui/README.md`

- [ ] **Step 1: Document practice problems in the README**

In `sandbox_ui/README.md`, in the Create-context wizard section (where the Exercise step is described), update the Exercise bullet to note the two groups, e.g.:

```markdown
- **Exercise** — an exercise (`exercise_<NN>.txt`) or a **practice problem**
  (`practice_<NN>.txt`) for the chosen course, shown as separate "Exercises" and
  "Practice problems" groups, or custom exercise text. The chosen kind is stored
  per conversation in `exercise_kind` (defaults to `exercise`).
```

And in the `POST /api/chat` field documentation, note the optional `"exercise_kind": "exercise"|"practice"` field (defaults to `"exercise"`).

- [ ] **Step 2: Run the full standalone test suite**

Run each, expecting `0 failed`:
```bash
python -m utils.test_curriculum
python -m utils.test_figures
python -m sandbox_ui.services.test_tutor_bridge_practice
python -m sandbox_ui.routes.test_validation_practice
```

- [ ] **Step 3: End-to-end smoke with a real practice file**

Create a throwaway practice file, start the app, and confirm the wizard + tutor path (as in Task 6 Step 9). Remove the throwaway file afterward (real practice content is captured separately).

- [ ] **Step 4: Commit**

```bash
git add sandbox_ui/README.md
git commit -m "docs(sandbox_ui): document practice problems"
```

---

## Self-Review Notes

- **Spec coverage:** resolver (Task 1), persistence column (Task 3), options API + preview (Task 4), wizard two-group UI (Task 6), tutor resolution + cache keys (Task 2), route plumbing (Task 5), README (Task 7), tests (Tasks 1/2/4). Figures explicitly out of scope (Global Constraints).
- **Kind values** consistently `"exercise"`/`"practice"`, defaulting to `"exercise"` at every boundary (JS default, route parse, DB read-back, tutor_bridge default).
- **Value encoding** consistently `kind:number` in the wizard `<select>`, parsed back in `saveCreateStep` and previewed in `fetchPreviewText`.
- **Backward compatibility:** existing exercise selections produce `exercise_kind="exercise"`; legacy rows read `NULL → "exercise"`; courses without practice files expose `[]` and omit the group.
