"""Shared validators for `course`, `exercise`, and `tutor` request params.

Used by both `routes/embed.py` (Step 3) and `routes/chat.py` (Step 5). Each
validator returns ``None`` on success or a dict describing the failure
(``{param, value, reason}``) so routes can map it to their preferred HTTP
response shape.
"""

from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CURRICULUM_DIR = _REPO_ROOT / "curriculum"
_TUTOR_PROMPTS_DIR = _REPO_ROOT / "tutor" / "prompts"

DEFAULT_TUTOR = "tutor_05"
DEFAULT_COURSE = "cities_and_climate_change"
DEFAULT_EXERCISE = "01"


def _list_courses() -> set[str]:
    if not _CURRICULUM_DIR.is_dir():
        return set()
    return {p.name for p in _CURRICULUM_DIR.iterdir() if p.is_dir()}


def _exercise_exists(course: str, exercise_number: str) -> bool:
    return (_CURRICULUM_DIR / course / f"exercise_{exercise_number}.txt").is_file()


def _tutor_prompt_exists(tutor: str) -> bool:
    return (_TUTOR_PROMPTS_DIR / f"{tutor}.txt").is_file()


def _err(param: str, value, reason: str) -> dict:
    return {"param": param, "value": value, "reason": reason}


def validate_course(course) -> dict | None:
    if not course:
        return _err("course", course, "missing")
    if course not in _list_courses():
        return _err("course", course, "no such course")
    return None


def validate_exercise(course, exercise) -> dict | None:
    if not exercise:
        return _err("exercise", exercise, "missing")
    if not (isinstance(exercise, str) and len(exercise) == 2 and exercise.isdigit()):
        return _err(
            "exercise", exercise, "must be a zero-padded 2-digit number (e.g. 04)"
        )
    if not _exercise_exists(course, exercise):
        return _err(
            "exercise", exercise, f"no exercise_{exercise}.txt under curriculum/{course}/"
        )
    return None


def validate_tutor(tutor) -> dict | None:
    if not tutor:
        return _err("tutor", tutor, "missing")
    if not _tutor_prompt_exists(tutor):
        return _err("tutor", tutor, "no such tutor prompt")
    return None


def load_course_name(course) -> str:
    """Display name for a course, read from curriculum/<course>/course_name.txt.

    Returns "" if the course is falsy or the file is missing/empty, so the
    banner degrades gracefully until each course_name.txt is filled in.
    """
    if not course:
        return ""
    path = _CURRICULUM_DIR / course / "course_name.txt"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def list_exercises(course) -> list[str]:
    """Sorted zero-padded 2-digit exercise numbers available for a course."""
    course_dir = _CURRICULUM_DIR / course if course else None
    if not course_dir or not course_dir.is_dir():
        return []
    nums: list[str] = []
    for p in course_dir.glob("exercise_*.txt"):
        num = p.stem.split("exercise_", 1)[-1]
        if len(num) == 2 and num.isdigit():
            nums.append(num)
    return sorted(nums)


def course_has_syllabus(course) -> bool:
    """True if the course ships a syllabus.txt that can be toggled into context."""
    if not course:
        return False
    return (_CURRICULUM_DIR / course / "syllabus.txt").is_file()


def list_tutors() -> list[str]:
    """Sorted tutor prompt stems available under tutor/prompts/."""
    if not _TUTOR_PROMPTS_DIR.is_dir():
        return []
    return sorted(p.stem for p in _TUTOR_PROMPTS_DIR.glob("*.txt"))


def list_context_options() -> dict:
    """Full option set for the test_ui Change-context switcher.

    Shape:
        {
          "courses": [
            {"slug": ..., "name": ..., "exercises": ["01", ...], "has_syllabus": bool},
            ...
          ],
          "tutors": ["tutor_01", ...],
        }
    """
    courses = []
    for slug in sorted(_list_courses()):
        courses.append(
            {
                "slug": slug,
                "name": load_course_name(slug),
                "exercises": list_exercises(slug),
                "has_syllabus": course_has_syllabus(slug),
            }
        )
    return {"courses": courses, "tutors": list_tutors()}
