"""LLM-based judge for humanities tutor transcripts."""

from __future__ import annotations

__all__ = ["JudgeError", "JudgeResult", "judge_transcript", "load_judge_prompt"]


def __getattr__(name: str):
    if name in __all__:
        from .run_judge_gpt import (
            JudgeError,
            JudgeResult,
            judge_transcript,
            load_judge_prompt,
        )

        exports = {
            "JudgeError": JudgeError,
            "JudgeResult": JudgeResult,
            "judge_transcript": judge_transcript,
            "load_judge_prompt": load_judge_prompt,
        }
        return exports[name]
    raise AttributeError(f"module 'judge' has no attribute {name!r}")