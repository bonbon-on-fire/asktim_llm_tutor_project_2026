"""GPT single-transcript judge wrapper (unified core)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from judge.run_judge_unified import (
    DEFAULT_JUDGE_PROMPT,
    DEFAULT_RUBRIC,
    JudgeError,
    JudgeResult,
    load_judge_prompt,
    judge_transcript_gpt,
)

judge_transcript = judge_transcript_gpt

__all__ = ["JudgeError", "JudgeResult", "judge_transcript", "load_judge_prompt"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python judge/run_judge_gpt.py <transcript_name>")
        print("Example: python judge/run_judge_gpt.py chaotic/chaotic_raw/transcript_01")
        raise SystemExit(0)
    transcript_name = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_JUDGE_PROMPT
    rubric = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_RUBRIC
    try:
        result = judge_transcript(transcript_name, prompt_name=prompt, rubric_name=rubric)
        print(f"Judged {transcript_name}: {result.total_score}/{result.max_score}")
        print(f"Output: {result.output_path}")
    except JudgeError as e:
        print(f"Error: {e}")
        raise SystemExit(1)


