"""GPT batch judge runner for batch_XX_YYY transcript sets.

Each batch file is judged as one combined transcript entity.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
load_dotenv(_REPO_ROOT / ".env")

try:
    from .run_judge_gpt import JudgeError, JudgeResult, judge_transcript
except ImportError:  # direct script-style import fallback
    from run_judge_gpt import JudgeError, JudgeResult, judge_transcript  # type: ignore

_BATCH_DIR = Path(__file__).resolve().parent / "transcript_batches"
_BATCH_OUTPUT_DIR = _REPO_ROOT / "transcripts" / "batch" / "gpt"
_TRANSCRIPTS_DIR = _REPO_ROOT / "transcripts"

# Simple in-file toggle for default batch type.
BATCH_TYPE = "02"
JUDGE_PROMPT = "judge_05"
JUDGE_RUBRIC = "rubric_05"


def _normalize_batch_type(value: str) -> str:
    text = (value or "").strip()
    if text in {"1", "2", "3"}:
        return f"0{text}"
    if text in {"01", "02", "03"}:
        return text
    raise JudgeError("batch_type must be one of: 01, 02, 03")


def _normalize_stem(stem: str) -> str:
    value = (stem or "").strip()
    if not value:
        raise JudgeError("Empty transcript entry found in batch file.")
    value = value.replace("\\", "/")
    if value.endswith(".json"):
        value = value[:-5]
    return value


def _read_batch_transcripts(batch_file_path: Path) -> list[str]:
    items: list[str] = []
    for line in batch_file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        items.append(_normalize_stem(stripped))
    if not items:
        raise JudgeError(f"No transcript entries found in batch file: {batch_file_path}")
    return items


def _batch_files_for_type(batch_type: str) -> list[Path]:
    normalized = _normalize_batch_type(batch_type)
    files = sorted(_BATCH_DIR.glob(f"batch_{normalized}_*.txt"))
    if not files:
        raise JudgeError(f"No batch files found for batch type {normalized} in {_BATCH_DIR}")
    return files


def _save_batch_output(
    *,
    batch_file: Path,
    combined_transcript: dict[str, object],
) -> Path:
    _BATCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_name = f"{batch_file.stem}.json"
    output_path = _BATCH_OUTPUT_DIR / output_name
    output_path.write_text(
        json.dumps(combined_transcript, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def _load_transcript(stem: str) -> dict[str, object]:
    path = _TRANSCRIPTS_DIR / f"{stem}.json"
    if not path.exists():
        raise JudgeError(f"Transcript not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise JudgeError(f"Transcript is not valid JSON: {path} ({error})") from error
    if not isinstance(data, dict):
        raise JudgeError(f"Transcript JSON must be an object: {path}")
    exchanges = data.get("exchanges")
    if not isinstance(exchanges, list) or not exchanges:
        raise JudgeError(f"Transcript must contain non-empty exchanges: {path}")
    return data


def _build_combined_transcript(*, batch_file: Path, stems: list[str], batch_type: str) -> dict[str, object]:
    combined_exchanges: list[dict[str, object]] = []
    members: list[dict[str, object]] = []
    turn_counter = 0
    for stem in stems:
        transcript = _load_transcript(stem)
        exchanges = transcript.get("exchanges")
        assert isinstance(exchanges, list)  # validated above
        turn_size = transcript.get("turn_size")
        if turn_size is None:
            turn_size = transcript.get("turns")
        members.append(
            {
                "tutor_prompt": transcript.get("tutor_prompt"),
                "student_persona": transcript.get("student_persona"),
                "course": transcript.get("course"),
                "exercise_number": transcript.get("exercise_number"),
                "turn_size": turn_size,
                "transcript": stem,
            }
        )
        for exchange in exchanges:
            if not isinstance(exchange, dict):
                continue
            turn_counter += 1
            combined_exchanges.append(
                {
                    "turn": turn_counter,
                    "student": str(exchange.get("student", "")),
                    "tutor": str(exchange.get("tutor", "")),
                    "source_transcript": stem,
                    "source_turn": exchange.get("turn"),
                }
            )

    if not combined_exchanges:
        raise JudgeError(f"No usable exchanges found for batch file: {batch_file}")

    exercise_lines = [
        "Batch judging mode: evaluate all included transcripts together as one entity.",
        f"Batch type: {batch_type}",
        f"Batch file: {batch_file.name}",
        "",
        "Included transcripts:",
    ]
    for member in members:
        exercise_lines.append(
            "- "
            f"{member['transcript']} "
            f"(persona={member.get('student_persona')}, course={member.get('course')}, exercise={member.get('exercise_number')}, turn_size={member.get('turn_size')})"
        )

    def _common_or_mixed(key: str) -> object:
        values = {str(member.get(key, "")).strip() for member in members}
        values.discard("")
        if len(values) == 1:
            return next(iter(values))
        return "mixed"

    return {
        "batch_members": members,
        "context": "Combined transcript bundle for comparative grading.",
        "exercise": "\n".join(exercise_lines),
        "turns": len(combined_exchanges),
        "exchanges": combined_exchanges,
    }


def _relative_stem(path: Path) -> str:
    rel = path.relative_to(_TRANSCRIPTS_DIR).as_posix()
    return rel[:-5] if rel.endswith(".json") else rel


def judge_transcript_batch(
    transcript_name: str,
    *,
    batch_file_path: str,
    prompt_name: str = "judge_05",
    rubric_name: str = "rubric_05",
    output_name: str | None = None,
) -> JudgeResult:
    del transcript_name  # Backward-compatible signature from single-transcript API.
    del output_name  # Batch outputs are stored as batch_<type>_<number>.json.
    batch_path = Path(batch_file_path)
    if not batch_path.is_absolute():
        batch_path = (_REPO_ROOT / batch_path).resolve()
    if not batch_path.exists():
        raise JudgeError(f"Batch file not found: {batch_path}")
    stems = _read_batch_transcripts(batch_path)
    parts = batch_path.stem.split("_")
    batch_type = parts[1] if len(parts) >= 3 else "unknown"
    combined = _build_combined_transcript(batch_file=batch_path, stems=stems, batch_type=batch_type)
    source_path = _save_batch_output(
        batch_file=batch_path,
        combined_transcript=combined,
    )
    return judge_transcript(
        _relative_stem(source_path),
        prompt_name=prompt_name,
        rubric_name=rubric_name,
        output_name=source_path.stem,  # keep batch_XX_YYY.json
    )


def run_batch_type(
    *,
    batch_type: str = BATCH_TYPE,
    prompt_name: str = JUDGE_PROMPT,
    rubric_name: str = JUDGE_RUBRIC,
) -> int:
    normalized = _normalize_batch_type(batch_type)
    files = _batch_files_for_type(normalized)
    print(
        f"[GPT Batch Judge] Running {len(files)} files for type={normalized} "
        f"prompt={prompt_name} rubric={rubric_name}"
    )
    for batch_file in files:
        stems = _read_batch_transcripts(batch_file)
        result = judge_transcript_batch(
            "unused",
            batch_file_path=str(batch_file),
            prompt_name=prompt_name,
            rubric_name=rubric_name,
        )
        print(
            "[GPT Batch Judge] "
            f"batch={batch_file.name} transcripts={len(stems)} "
            f"saved={(_BATCH_OUTPUT_DIR / (batch_file.stem + '.json')).relative_to(_REPO_ROOT)} "
            f"score={result.total_score}/{result.max_score}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GPT judging for all batch files of a given type.")
    parser.add_argument(
        "--batch-type",
        default=BATCH_TYPE,
        help="Batch type to run: 01, 02, or 03 (default: BATCH_TYPE in file).",
    )
    parser.add_argument("--prompt", default=JUDGE_PROMPT, help="Judge prompt stem.")
    parser.add_argument("--rubric", default=JUDGE_RUBRIC, help="Judge rubric stem.")
    args = parser.parse_args(argv)

    try:
        return run_batch_type(
            batch_type=args.batch_type,
            prompt_name=args.prompt,
            rubric_name=args.rubric,
        )
    except KeyboardInterrupt:
        print("\nGPT batch judging interrupted.")
        return 130
    except JudgeError as error:
        print(f"Judge failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
