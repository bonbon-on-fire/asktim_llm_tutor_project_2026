"""
Build transcript-level GPT vs Claude score comparison chart.

Usage:
    python -m visualization.run_visualization
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GradeRow:
    # Source metadata copied from judged transcript JSON files.
    tutor_prompt: str
    student_persona: str
    course: str
    exercise_number: str
    judge_prompt: str
    judge_rubric: str
    transcript_name: str
    total_score: float
    max_score: float

    @property
    def persona_type(self) -> str:
        # chaotic_04 -> chaotic
        return (self.student_persona.split("_", 1)[0] or self.student_persona).strip()

    @property
    def exercise_label(self) -> str:
        return f"{self.course}:{self.exercise_number}"

    @property
    def transcript_key(self) -> str:
        # Key chosen to align the same run across model outputs.
        return "|".join(
            [
                self.student_persona,
                self.course,
                self.exercise_number,
                self.transcript_name,
            ]
        )


def _parse_score(x: str) -> float:
    try:
        return float(str(x or "").strip())
    except (TypeError, ValueError):
        return float("nan")


def _read_judged_transcript_json(path: Path) -> GradeRow | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    grade = raw.get("grade")
    if not isinstance(grade, dict):
        return None

    return GradeRow(
        tutor_prompt=str(raw.get("tutor_prompt", "")).strip(),
        student_persona=str(raw.get("student_persona", "")).strip(),
        course=str(raw.get("course", "")).strip(),
        exercise_number=str(raw.get("exercise_number", "")).strip(),
        judge_prompt=str(raw.get("judge_prompt", "")).strip(),
        judge_rubric=str(raw.get("judge_rubric", "")).strip(),
        transcript_name=path.stem.strip(),
        total_score=_parse_score(grade.get("total_score")),
        max_score=_parse_score(grade.get("max_score")),
    )


def _read_provider_rows(
    *,
    transcripts_dir: Path,
    provider_suffix: str,
) -> list[GradeRow]:
    # provider_suffix examples: "gpt", "claude"
    # Path pattern: transcripts/<persona_type>/<persona_type>_<provider_suffix>/transcript_XX.json
    rows: list[GradeRow] = []
    pattern = f"*/*_{provider_suffix}/transcript_*.json"
    for transcript_path in sorted(transcripts_dir.glob(pattern)):
        row = _read_judged_transcript_json(transcript_path)
        if row is None:
            continue
        rows.append(row)

    return rows


def _sort_key(row: GradeRow) -> tuple:
    # Stable ordering across charts.
    tnum = int(row.transcript_name.split("_")[-1]) if "_" in row.transcript_name else 0
    ex_num = int(row.exercise_number) if row.exercise_number.isdigit() else 0
    return (row.persona_type, row.student_persona, row.course, ex_num, tnum)


def _safe_import_matplotlib():
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "matplotlib is required for visualization. "
            "Install with: python -m pip install matplotlib"
        ) from e
    return plt


def _line_chart_grades_per_transcript(
    *,
    gpt_rows: list[GradeRow],
    claude_rows: list[GradeRow],
    out_dir: Path,
) -> None:
    plt = _safe_import_matplotlib()

    # Align transcript series by composite key so lines are comparable.
    gpt_by_key = {r.transcript_key: r for r in gpt_rows}
    claude_by_key = {r.transcript_key: r for r in claude_rows}

    all_keys = sorted(set(gpt_by_key.keys()) | set(claude_by_key.keys()))
    all_keys = sorted(
        all_keys,
        key=lambda k: _sort_key(gpt_by_key.get(k) or claude_by_key[k]),
    )

    x = list(range(len(all_keys)))
    y_gpt = [gpt_by_key[k].total_score if k in gpt_by_key else float("nan") for k in all_keys]
    y_claude = [claude_by_key[k].total_score if k in claude_by_key else float("nan") for k in all_keys]

    fig, ax = plt.subplots(figsize=(16, 7))
    ax.plot(x, y_gpt, label="GPT", color="#a65dea", linewidth=1.8, marker="o", markersize=3)
    ax.plot(x, y_claude, label="Claude", color="#ff893a", linewidth=1.8, marker="o", markersize=3)
    ax.set_title("Grades Per Transcript: GPT vs Claude")
    ax.set_xlabel("Transcript Index (sorted by persona/course/exercise/transcript)")
    ax.set_ylabel("Total Score")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "grades_per_transcript_gpt_vs_claude.png", dpi=150)
    plt.close(fig)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    transcripts_dir = repo_root / "transcripts"
    out_dir = repo_root / "visualization" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    gpt_rows = _read_provider_rows(transcripts_dir=transcripts_dir, provider_suffix="gpt")
    claude_rows = _read_provider_rows(transcripts_dir=transcripts_dir, provider_suffix="claude")

    if not gpt_rows and not claude_rows:
        raise RuntimeError(
            "No judged transcript JSON files found for GPT or Claude under transcripts/<persona_type>/."
        )

    _line_chart_grades_per_transcript(
        gpt_rows=gpt_rows,
        claude_rows=claude_rows,
        out_dir=out_dir,
    )
    print(f"[Done] Wrote visualizations to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
