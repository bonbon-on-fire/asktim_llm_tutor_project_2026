"""
Interactive mini judge runner: randomly samples N (transcript, turn) pairs,
regenerates the tutor reply at each pivot turn with a new prompt,
then compares original vs new using a comparison-based mini judge.

Prints a per-sample YES/NO verdict and a final summary. Nothing is written to disk.

Run with:
    python -m ui.run_ui_judge_mini
"""

from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
load_dotenv(_REPO_ROOT / ".env")

from dataclasses import dataclass

from judge.run_judge_mini import MiniJudgeError, compare_turn, discover_rubrics  # noqa: E402
from tutor.run_tutor import create_tutor_graph, get_tutor_reply, load_system_prompt  # noqa: E402
from tutor.run_tutor_mini import (  # noqa: E402
    _RAW_SUBDIR_BY_PERSONA_TYPE,
    _discover_tutor_prompts,
    _require_tutor_key,
    build_histories_resume_pivot,
)
from ui.cli_utils import confirm_proceed, prompt_integer, prompt_single_selection  # noqa: E402

TRANSCRIPTS_DIR = _REPO_ROOT / "transcripts"


def _discover_raw_transcripts() -> list[Path]:
    """Return all raw transcript JSON files across all persona raw folders."""
    raw_paths: list[Path] = []
    for persona_type, subdir in _RAW_SUBDIR_BY_PERSONA_TYPE.items():
        folder = TRANSCRIPTS_DIR / persona_type / subdir
        if folder.exists():
            raw_paths.extend(sorted(folder.glob("transcript_*.json")))
    return raw_paths


def _load_transcript(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _max_turn(exchanges: list[dict]) -> int:
    best = 0
    for ex in exchanges:
        if isinstance(ex, dict):
            t = ex.get("turn")
            if isinstance(t, int) and t > best:
                best = t
    return best


def _get_exchange_at_turn(exchanges: list[dict], turn: int) -> dict[str, Any] | None:
    for ex in exchanges:
        if isinstance(ex, dict) and ex.get("turn") == turn:
            return ex
    return None


@dataclass
class _SampleResult:
    index: int
    rel_path: str
    turn: int
    student: str
    original_reply: str
    new_reply: str
    new_is_better: bool
    reason: str


def _run_one_sample(
    *,
    transcript_path: Path,
    tutor_prompt: str,
    tutor_provider: str,
    rubric_name: str,
    judge_provider: str,
    sample_index: int,
    total_samples: int,
) -> _SampleResult | None:
    """
    Run one comparison sample. Returns a _SampleResult, or None on skip/error.
    """
    print(f"[{sample_index}/{total_samples}] Running...", end="  ", flush=True)

    data = _load_transcript(transcript_path)
    exchanges = data.get("exchanges")
    if not isinstance(exchanges, list) or not exchanges:
        print(f"SKIP  {transcript_path.name}  (no exchanges)")
        return None

    max_t = _max_turn(exchanges)
    if max_t < 1:
        print(f"SKIP  {transcript_path.name}  (no valid turns)")
        return None

    pivot_turn = random.randint(1, max_t)
    ex = _get_exchange_at_turn(exchanges, pivot_turn)
    if ex is None:
        print(f"SKIP  {transcript_path.name}  turn={pivot_turn}  (turn missing)")
        return None

    original_reply = ex.get("tutor", "")
    if not isinstance(original_reply, str):
        original_reply = str(original_reply)

    assignment_text: str = data.get("exercise", "") or ""
    if not isinstance(assignment_text, str):
        assignment_text = str(assignment_text)

    # Build history up to pivot; student message at pivot is already appended.
    try:
        tutor_messages, _, student_text = build_histories_resume_pivot(
            exchanges, pivot_turn=pivot_turn
        )
    except (ValueError, KeyError) as e:
        print(f"SKIP  {transcript_path.name}  turn={pivot_turn}  (history: {e})")
        return None

    # Build tutor graph with this transcript's assignment injected.
    system_prompt = load_system_prompt(
        tutor_prompt,
        assignment_override=assignment_text if assignment_text else None,
    )
    tutor_graph = create_tutor_graph(system_prompt, provider=tutor_provider)

    # Generate new tutor reply.
    try:
        _, new_reply = get_tutor_reply(tutor_messages, graph=tutor_graph)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR  {transcript_path.name}  turn={pivot_turn}  (tutor: {e})")
        return None

    # Compare original vs new.
    try:
        verdict = compare_turn(
            student_message=student_text,
            original_tutor_reply=original_reply,
            new_tutor_reply=new_reply,
            rubric_name=rubric_name,
            provider=judge_provider,
        )
    except MiniJudgeError as e:
        print(f"ERROR  {transcript_path.name}  turn={pivot_turn}  (judge: {e})")
        return None

    print(f"done  ({transcript_path.parent.name}/{transcript_path.name}  turn={pivot_turn})")
    return _SampleResult(
        index=sample_index,
        rel_path=str(transcript_path.relative_to(_REPO_ROOT)),
        turn=pivot_turn,
        student=student_text,
        original_reply=original_reply,
        new_reply=new_reply,
        new_is_better=verdict.new_is_better,
        reason=verdict.reason,
    )


def main() -> int:
    print("=== Mini Tutor Comparison Judge ===")
    print("Randomly samples turns, regenerates with new tutor prompt, compares to original.\n")

    prompts = _discover_tutor_prompts()
    if not prompts:
        print("No tutor prompts found in tutor/prompts/")
        return 1

    tutor_prompt = prompt_single_selection("New tutor prompt", prompts, required=True)
    if not tutor_prompt:
        return 1

    tutor_provider = prompt_single_selection("Tutor provider", ["gpt", "claude"], required=True)
    if not tutor_provider:
        return 1

    try:
        _require_tutor_key(tutor_provider)
    except RuntimeError as e:
        print(str(e))
        return 1

    rubrics = discover_rubrics()
    if not rubrics:
        print("No rubrics found in judge/rubrics/")
        return 1

    rubric_name = prompt_single_selection("Judge rubric", rubrics, required=True)
    if not rubric_name:
        return 1

    judge_provider = prompt_single_selection("Judge provider", ["gpt", "claude"], required=True)
    if not judge_provider:
        return 1

    if judge_provider == "gpt":
        if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")):
            print("OPENAI_API_KEY is required for GPT judge.")
            return 1
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY is required for Claude judge.")
            return 1

    n_samples = prompt_integer("Number of random samples", min_value=1, max_value=100)
    if n_samples is None:
        return 1

    raw_paths = _discover_raw_transcripts()
    if not raw_paths:
        print(f"No raw transcripts found under {TRANSCRIPTS_DIR}")
        return 1

    summary = (
        f"New tutor prompt : {tutor_prompt} ({tutor_provider.upper()})\n"
        f"  • Judge rubric : {rubric_name}\n"
        f"  • Judge        : {judge_provider.upper()}\n"
        f"  • Samples      : {n_samples} random (transcript, turn) pairs\n"
        f"  • Pool         : {len(raw_paths)} raw transcripts"
    )
    if not confirm_proceed(summary):
        print("Cancelled.")
        return 0

    # --- Collect all results ---
    print()
    samples: list[_SampleResult] = []
    errors = 0

    for i in range(1, n_samples + 1):
        transcript_path = random.choice(raw_paths)
        outcome = _run_one_sample(
            transcript_path=transcript_path,
            tutor_prompt=tutor_prompt,
            tutor_provider=tutor_provider,
            rubric_name=rubric_name,
            judge_provider=judge_provider,
            sample_index=i,
            total_samples=n_samples,
        )
        if outcome is None:
            errors += 1
        else:
            samples.append(outcome)

    if not samples:
        print("\nNo samples completed successfully.")
        return 1

    sep = "─" * 72

    # --- Section 1: conversations ---
    print(f"\n{'═' * 72}")
    print("  CONVERSATIONS")
    print(f"{'═' * 72}")
    for s in samples:
        print(f"\n[{s.index}/{n_samples}]  {s.rel_path}  turn={s.turn}")
        print(sep)
        print("STUDENT")
        print(s.student)
        print(sep)
        print("ORIGINAL TUTOR")
        print(s.original_reply)
        print(sep)
        print("NEW TUTOR")
        print(s.new_reply)
        print(sep)

    # --- Section 2: verdicts ---
    print(f"\n{'═' * 72}")
    print("  VERDICTS")
    print(f"{'═' * 72}")
    for s in samples:
        verdict = "YES" if s.new_is_better else "NO "
        print(f"[{s.index}/{n_samples}]  {s.rel_path}  turn={s.turn}")
        print(f"  {verdict}  \"{s.reason}\"")

    # --- Section 3: overall stats ---
    better = sum(s.new_is_better for s in samples)
    total_judged = len(samples)
    pct = f" ({100 * better // total_judged}%)" if total_judged else ""
    print(f"\n{'═' * 72}")
    print(
        f"  Judged  : {total_judged}/{n_samples}  (errors/skips: {errors})\n"
        f"  Better  : {better}/{total_judged}{pct}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
