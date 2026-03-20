"""Claude-based judge for humanities tutor transcripts."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict

from judge.run_judge_gpt import (
    JudgeError,
    JudgeResult,
    TRANSCRIPTS_DIR,
    _env_truthy,
    _format_conversation_for_judge,
    _judge_repair_prompt,
    _order_grade_payload,
    _parse_json_from_model_output,
    _sanitize_grade_payload,
    _validate_grade_payload,
    load_judge_prompt,
)
from datetime import datetime, timezone

_DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"

def _require_anthropic_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is required but not set.")
    return key


class _JudgeState(TypedDict):
    attempts: int
    system_prompt: str
    conversation_text: str
    num_turns: int
    last_output: NotRequired[str]
    last_error: NotRequired[str]
    grade_json: NotRequired[dict[str, Any]]


def _create_judge_graph(*, model_name: str, api_key: str, enforce_sub_criterion_ids: bool):
    model = ChatAnthropic(model=model_name, temperature=0, api_key=api_key)

    def judge_node(state: _JudgeState) -> dict[str, Any]:
        messages = [SystemMessage(content=state["system_prompt"])]
        if state.get("last_error") and state.get("last_output"):
            messages.append(
                HumanMessage(
                    content=_judge_repair_prompt(state["last_error"])
                    + "\n\nPrevious JSON (to repair):\n"
                    + state["last_output"]
                )
            )
        messages.append(HumanMessage(content=state["conversation_text"]))
        resp = model.invoke(messages)
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return {"last_output": content, "attempts": int(state.get("attempts", 0)) + 1}

    def validate_node(state: _JudgeState) -> dict[str, Any]:
        out = state.get("last_output", "")
        try:
            parsed = _parse_json_from_model_output(out)
            parsed = _sanitize_grade_payload(parsed)
            validated = _validate_grade_payload(
                parsed,
                num_turns=int(state["num_turns"]),
                enforce_sub_criterion_ids=enforce_sub_criterion_ids,
            )
            ordered = _order_grade_payload(validated)
            return {"grade_json": ordered, "last_error": None}
        except JudgeError as e:
            return {"last_error": str(e), "grade_json": None}

    graph = StateGraph(_JudgeState)
    graph.add_node("judge", judge_node)
    graph.add_node("validate", validate_node)
    graph.add_edge(START, "judge")
    graph.add_edge("judge", "validate")

    def _route(state: _JudgeState) -> str:
        if state.get("grade_json") is not None:
            return END
        if int(state.get("attempts", 0)) >= 2:
            return END
        return "judge"

    graph.add_conditional_edges("validate", _route, {"judge": "judge", END: END})
    return graph.compile()


def judge_transcript(
    transcript_name: str,
    *,
    prompt_name: str = "judge_03",
    rubric_name: str = "rubric_04",
) -> JudgeResult:
    """
    Score one transcript by relative path (without .json) under transcripts/.

    Examples: ``"chaotic/transcript_01"`` or ``"transcript_01"``.

    Side effect: updates the transcript JSON in-place by adding a top-level
    ``grade`` object.
    """
    name = (transcript_name or "").strip()
    if not name:
        raise JudgeError("transcript_name is required (path without .json).")

    transcript_path = TRANSCRIPTS_DIR / f"{name}.json"
    if not transcript_path.exists():
        raise JudgeError(f"Transcript not found: {transcript_path}")

    try:
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise JudgeError(f"Transcript is not valid JSON: {e}") from e
    if not isinstance(transcript, dict):
        raise JudgeError("Transcript JSON must be an object.")
    if "grade" in transcript:
        raise JudgeError("Transcript already contains a top-level 'grade' key; refusing to overwrite.")

    exchanges = transcript.get("exchanges")
    if not isinstance(exchanges, list) or not exchanges:
        raise JudgeError("Transcript must contain a non-empty 'exchanges' array.")

    api_key = _require_anthropic_api_key()
    model_name = os.environ.get("ANTHROPIC_MODEL", _DEFAULT_ANTHROPIC_MODEL)

    system_prompt = load_judge_prompt(prompt_name=prompt_name, rubric_name=rubric_name)
    conversation_text = _format_conversation_for_judge(transcript)

    enforce_sub_criterion_ids = rubric_name.strip().lower() == "rubric_04"
    graph = _create_judge_graph(
        model_name=model_name,
        api_key=api_key,
        enforce_sub_criterion_ids=enforce_sub_criterion_ids,
    )
    result = graph.invoke(
        {
            "attempts": 0,
            "system_prompt": system_prompt,
            "conversation_text": conversation_text,
            "num_turns": len(exchanges),
        }
    )
    grade_json = result.get("grade_json")
    if grade_json is None:
        raise JudgeError(f"Judge failed to produce valid grade JSON. Last error: {result.get('last_error')}")

    grade_payload = dict(grade_json)
    grade_payload["model"] = {"provider": "anthropic", "model": model_name, "temperature": 0}
    grade_payload["judge_llm_calls"] = int(result.get("attempts", 0))
    if _env_truthy("JUDGE_INCLUDE_TIMESTAMP"):
        grade_payload["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    grade_payload = _order_grade_payload(grade_payload)

    transcript["grade"] = grade_payload
    transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return JudgeResult(
        total_score=int(grade_payload["total_score"]),
        max_score=int(grade_payload["max_score"]),
    )
