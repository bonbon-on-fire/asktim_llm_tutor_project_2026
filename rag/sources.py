"""Local-file source reader for RAG ingestion.

Returns the course-level material that should be *retrievable* — ``course.txt``,
``syllabus.txt``, and every ``lectures/*.txt`` — as labeled ``(source, text)``
documents. The exercise prompt and figures are intentionally excluded: they stay
local and always-in-context, never in the RAG index (see PLANNING Phase 11).
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CURRICULUM_ROOT = _REPO_ROOT / "curriculum"

Doc = tuple[str, str]  # (source_label, text)


def load_local_docs(course: str, curriculum_root: Path | str | None = None) -> list[Doc]:
    """Collect local course/syllabus/lecture text as labeled documents."""
    root = Path(curriculum_root) if curriculum_root is not None else _DEFAULT_CURRICULUM_ROOT
    course_dir = root / course
    docs: list[Doc] = []

    for name in ("course.txt", "syllabus.txt"):
        path = course_dir / name
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                docs.append((f"local:{path.stem}", text))

    lectures_dir = course_dir / "lectures"
    if lectures_dir.is_dir():
        for path in sorted(lectures_dir.glob("*.txt")):
            text = path.read_text(encoding="utf-8").strip()
            if text:
                docs.append((f"local:{path.stem}", text))

    return docs
