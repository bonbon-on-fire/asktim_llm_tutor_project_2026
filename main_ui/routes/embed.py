"""GET /embed — main iframe entry point.

Validates `course`, `exercise`, and optional `tutor` query params against the
on-disk curriculum and tutor folders, then renders the placeholder
`embed.html` template. Real chat UI lands in Step 6.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, render_template, request


_REPO_ROOT = Path(__file__).resolve().parents[2]
_CURRICULUM_DIR = _REPO_ROOT / "curriculum"
_TUTOR_PROMPTS_DIR = _REPO_ROOT / "tutor" / "prompts"

DEFAULT_TUTOR = "tutor_05"

embed_bp = Blueprint("embed", __name__)


def _list_courses() -> set[str]:
    if not _CURRICULUM_DIR.is_dir():
        return set()
    return {p.name for p in _CURRICULUM_DIR.iterdir() if p.is_dir()}


def _exercise_exists(course: str, exercise_number: str) -> bool:
    return (_CURRICULUM_DIR / course / f"exercise_{exercise_number}.txt").is_file()


def _tutor_prompt_exists(tutor: str) -> bool:
    return (_TUTOR_PROMPTS_DIR / f"{tutor}.txt").is_file()


def _bad_param(name: str, value, reason: str):
    body = {"error": "invalid_param", "param": name, "value": value, "reason": reason}
    return jsonify(body), 404


@embed_bp.get("/embed")
def embed():
    course = request.args.get("course")
    exercise = request.args.get("exercise")
    tutor = request.args.get("tutor") or DEFAULT_TUTOR

    if not course:
        return _bad_param("course", course, "missing")
    if course not in _list_courses():
        return _bad_param("course", course, "no such course")

    if not exercise:
        return _bad_param("exercise", exercise, "missing")
    if not (len(exercise) == 2 and exercise.isdigit()):
        return _bad_param(
            "exercise", exercise, "must be a zero-padded 2-digit number (e.g. 04)"
        )
    if not _exercise_exists(course, exercise):
        return _bad_param(
            "exercise", exercise, f"no exercise_{exercise}.txt under curriculum/{course}/"
        )

    if not _tutor_prompt_exists(tutor):
        return _bad_param("tutor", tutor, "no such tutor prompt")

    tutor_config = {"course": course, "exercise": exercise, "tutor": tutor}
    return render_template(
        "embed.html",
        course=course,
        exercise=exercise,
        tutor=tutor,
        tutor_config=tutor_config,
    )
