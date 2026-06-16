"""Canonical curriculum path resolution shared across runners and web apps.

Exercise prompts live under ``curriculum/<course>/exercises/exercise_<NN>.txt``
(a subfolder, consistent with ``figures/`` and ``lectures/``). Previously they
sat loose at the top of the course folder; this module is the single place that
knows the layout, so the six call sites that used to duplicate
``course_dir / f"exercise_{n}.txt"`` now share one resolver.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CURRICULUM_ROOT = _REPO_ROOT / "curriculum"

# exercise_<NN>.txt — exactly two digits.
_EXERCISE_NAME_RE = re.compile(r"^exercise_(\d{2})\.txt$")


def _root(curriculum_root: Path | str | None) -> Path:
    return Path(curriculum_root) if curriculum_root is not None else _DEFAULT_CURRICULUM_ROOT


def course_dir(course: str, curriculum_root: Path | str | None = None) -> Path:
    """Return the course folder path (``curriculum/<course>/``)."""
    return _root(curriculum_root) / course


def exercises_dir(course: str, curriculum_root: Path | str | None = None) -> Path:
    """Return the exercises folder path (``curriculum/<course>/exercises/``)."""
    return course_dir(course, curriculum_root) / "exercises"


def exercise_path(
    course: str,
    exercise_number: str,
    curriculum_root: Path | str | None = None,
) -> Path:
    """Return the path to a course's exercise file (existence not guaranteed)."""
    return exercises_dir(course, curriculum_root) / f"exercise_{exercise_number}.txt"


def exercise_exists(
    course: str,
    exercise_number: str,
    curriculum_root: Path | str | None = None,
) -> bool:
    """True when the exercise file exists on disk."""
    if not course or not exercise_number:
        return False
    return exercise_path(course, exercise_number, curriculum_root).is_file()


def read_exercise(
    course: str,
    exercise_number: str,
    curriculum_root: Path | str | None = None,
) -> str:
    """Read an exercise file's text, or ``""`` when absent."""
    path = exercise_path(course, exercise_number, curriculum_root)
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def discover_exercises(
    course: str,
    curriculum_root: Path | str | None = None,
) -> list[str]:
    """Return sorted zero-padded 2-digit exercise numbers for a course (e.g. ``['01', '02']``)."""
    folder = exercises_dir(course, curriculum_root)
    if not folder.is_dir():
        return []
    nums: list[str] = []
    for path in folder.glob("exercise_*.txt"):
        m = _EXERCISE_NAME_RE.match(path.name)
        if m:
            nums.append(m.group(1))
    return sorted(nums)


def list_courses(curriculum_root: Path | str | None = None) -> list[str]:
    """Return sorted course folder names under the curriculum root."""
    root = _root(curriculum_root)
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir())
