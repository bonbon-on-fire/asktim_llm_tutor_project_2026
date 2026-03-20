"""
Transcripts UI - Flask app to navigate tutor transcripts with GPT/Claude grades.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from flask import Flask, jsonify, render_template

app = Flask(__name__, static_folder="static", template_folder="templates")

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_transcripts_dir() -> Path:
    if os.environ.get("TRANSCRIPTS_DIR"):
        return Path(os.environ["TRANSCRIPTS_DIR"]).resolve()

    candidates = [
        BASE_DIR / "transcripts",
        Path.cwd() / "transcripts",
        Path.cwd().parent / "transcripts",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return BASE_DIR / "transcripts"


TRANSCRIPTS_DIR = _resolve_transcripts_dir()


def _discover_persona_bases() -> list[str]:
    if not TRANSCRIPTS_DIR.is_dir():
        return []

    personas: list[str] = []
    for persona_dir in sorted(p for p in TRANSCRIPTS_DIR.iterdir() if p.is_dir()):
        persona = persona_dir.name
        gpt_dir = persona_dir / f"{persona}_gpt"
        claude_dir = persona_dir / f"{persona}_claude"
        if gpt_dir.is_dir() or claude_dir.is_dir():
            personas.append(persona)
    return personas


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def _grade_summary(data: dict | None) -> dict | None:
    if not data or "grade" not in data or not isinstance(data["grade"], dict):
        return None
    g = data["grade"]
    return {
        "total_score": g.get("total_score"),
        "max_score": g.get("max_score"),
        "total_base_score": g.get("total_base_score"),
        "max_base_score": g.get("max_base_score"),
        # New rubric style (malus)
        "total_malus": g.get("total_malus", 0),
        "max_malus": g.get("max_malus", 0),
        # Backward-compatible fields (bonus)
        "total_bonus": g.get("total_bonus", 0),
        "max_bonus": g.get("max_bonus", 0),
        "model": g.get("model"),
        "overview": g.get("overview", []),
        "sections": g.get("sections"),
    }


def _extract_display_number(stem: str) -> str:
    match = re.match(r"^transcript_(\d+)", stem)
    if not match:
        return stem
    return match.group(1)


def _stem_sort_key(stem: str) -> tuple[int, int, str]:
    match = re.match(r"^transcript_(\d+)", stem)
    if not match:
        return (1, 0, stem)
    return (0, int(match.group(1)), stem)


def _json_stems(path: Path) -> set[str]:
    if not path.is_dir():
        return set()
    return {f.stem for f in path.glob("*.json")}


def _transcript_path_for(*, persona: str, provider: str, stem: str) -> Path:
    return TRANSCRIPTS_DIR / persona / f"{persona}_{provider}" / f"{stem}.json"


def list_transcripts() -> list[dict]:
    out: list[dict] = []
    for persona in _discover_persona_bases():
        gpt_dir = TRANSCRIPTS_DIR / persona / f"{persona}_gpt"
        claude_dir = TRANSCRIPTS_DIR / persona / f"{persona}_claude"
        stems = sorted(_json_stems(gpt_dir) | _json_stems(claude_dir), key=_stem_sort_key)

        for stem in stems:
            gpt_data = _load_json(_transcript_path_for(persona=persona, provider="gpt", stem=stem))
            claude_data = _load_json(_transcript_path_for(persona=persona, provider="claude", stem=stem))
            gpt_grade = _grade_summary(gpt_data)
            claude_grade = _grade_summary(claude_data)

            meta_source = gpt_data or claude_data or {}
            meta = {k: v for k, v in meta_source.items() if k not in ("exchanges", "grade")}
            out.append(
                {
                    "persona": persona,
                    # Route key for exact judged transcript stem
                    "number": stem,
                    # Human-friendly transcript number (if available)
                    "display_number": _extract_display_number(stem),
                    "metadata": meta,
                    "gpt_grade": gpt_grade,
                    "claude_grade": claude_grade,
                    "gpt_score": gpt_grade["total_score"] if gpt_grade else None,
                    "gpt_max": gpt_grade["max_score"] if gpt_grade else None,
                    "claude_score": claude_grade["total_score"] if claude_grade else None,
                    "claude_max": claude_grade["max_score"] if claude_grade else None,
                }
            )
    return out


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/transcripts")
def api_list_transcripts():
    return jsonify(list_transcripts())


@app.route("/api/transcripts/<persona>/<num>")
def api_get_transcript(persona: str, num: str):
    if persona not in _discover_persona_bases():
        return jsonify({"error": "Unknown persona"}), 404

    gpt_data = _load_json(_transcript_path_for(persona=persona, provider="gpt", stem=num))
    claude_data = _load_json(_transcript_path_for(persona=persona, provider="claude", stem=num))
    if not gpt_data and not claude_data:
        return jsonify({"error": "Transcript not found"}), 404

    primary = gpt_data or claude_data or {}
    return jsonify(
        {
            "persona": persona,
            "number": num,
            "display_number": _extract_display_number(num),
            "metadata": {k: v for k, v in primary.items() if k not in ("exchanges", "grade")},
            "exchanges": (gpt_data or claude_data or {}).get("exchanges", []),
            "grade_gpt": _grade_summary(gpt_data),
            "grade_claude": _grade_summary(claude_data),
        }
    )


@app.route("/transcript/<persona>/<num>")
def transcript_page(persona: str, num: str):
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
