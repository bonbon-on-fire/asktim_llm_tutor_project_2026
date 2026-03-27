"""GPT-based judge for humanities tutor transcripts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

warnings.filterwarnings(
    "ignore",
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3\.14 or greater\.",
    category=UserWarning,
)

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
load_dotenv(_REPO_ROOT / ".env")

try:
    from .run_judge_claude import (
        JudgeError,
        JudgeResult,
        TRANSCRIPTS_DIR,
        _default_output_path,
        _extract_text_from_model_content,
        _env_truthy,
        _format_conversation_for_judge,
        _judge_repair_prompt,
        _order_grade_payload,
        _parse_json_from_model_output,
        _sanitize_grade_payload,
        _validate_grade_payload,
        load_judge_prompt,
    )
except ImportError:  # direct script-style import fallback
    from run_judge_claude import (  # type: ignore
        JudgeError,
        JudgeResult,
        TRANSCRIPTS_DIR,
        _default_output_path,
        _extract_text_from_model_content,
        _env_truthy,
        _format_conversation_for_judge,
        _judge_repair_prompt,
        _order_grade_payload,
        _parse_json_from_model_output,
        _sanitize_grade_payload,
        _validate_grade_payload,
        load_judge_prompt,
    )

_DEFAULT_OPENAI_MODEL = "gpt-5.2"
_MAX_ATTEMPTS = 3


def _require_openai_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    if not key:
        raise JudgeError("OPENAI_API_KEY (or OPENAI_KEY) environment variable is required but not set.")
    return key


class _JudgeState(TypedDict):
    attempts: int
    system_prompt: str
    conversation_text: str
    num_turns: int
    last_output: NotRequired[str]
    last_error: NotRequired[str]
    grade_json: NotRequired[dict[str, Any]]


def _build_openai_model(*, model_name: str, api_key: str):
    effort = os.environ.get("JUDGE_OPENAI_REASONING_EFFORT", "medium").strip().lower()
    if effort in {"low", "medium", "high", "off"}:
        try:
            return ChatOpenAI(
                model=model_name,
                temperature=0,
                api_key=api_key,
                model_kwargs={"reasoning": {"effort": effort}},
            )
        except TypeError:
            pass
    return ChatOpenAI(model=model_name, temperature=0, api_key=api_key)


def _create_judge_graph(*, model_name: str, api_key: str, enforce_sub_criterion_ids: bool, rubric_name: str):
    model = _build_openai_model(model_name=model_name, api_key=api_key)

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
        content = _extract_text_from_model_content(resp.content)
        return {"last_output": content, "attempts": int(state.get("attempts", 0)) + 1}

    def validate_node(state: _JudgeState) -> dict[str, Any]:
        try:
            parsed = _parse_json_from_model_output(state.get("last_output", ""))
            parsed = _sanitize_grade_payload(parsed)
            validated = _validate_grade_payload(
                parsed,
                num_turns=int(state["num_turns"]),
                enforce_sub_criterion_ids=enforce_sub_criterion_ids,
                rubric_name=rubric_name,
            )
            return {"grade_json": _order_grade_payload(validated), "last_error": None}
        except JudgeError as e:
            return {"grade_json": None, "last_error": str(e)}

    graph = StateGraph(_JudgeState)
    graph.add_node("judge", judge_node)
    graph.add_node("validate", validate_node)
    graph.add_edge(START, "judge")
    graph.add_edge("judge", "validate")

    def route(state: _JudgeState) -> str:
        if state.get("grade_json") is not None:
            return END
        return END if int(state.get("attempts", 0)) >= _MAX_ATTEMPTS else "judge"

    graph.add_conditional_edges("validate", route, {"judge": "judge", END: END})
    return graph.compile()


def judge_transcript(
    transcript_name: str,
    *,
    prompt_name: str = "judge_05",
    rubric_name: str = "rubric_05",
    output_name: str | None = None,
) -> JudgeResult:
    name = (transcript_name or "").strip()
    if not name:
        raise JudgeError("transcript_name is required (path without .json).")
    name = name.replace("\\", "/")
    if name.endswith(".json"):
        name = name[:-5]

    source_path = TRANSCRIPTS_DIR / f"{name}.json"
    if not source_path.exists():
        raise JudgeError(f"Transcript not found: {source_path}")

    try:
        transcript = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise JudgeError(f"Transcript is not valid JSON: {e}") from e
    if not isinstance(transcript, dict):
        raise JudgeError("Transcript JSON must be an object.")

    exchanges = transcript.get("exchanges")
    if not isinstance(exchanges, list) or not exchanges:
        raise JudgeError("Transcript must contain a non-empty 'exchanges' array.")

    normalized_rubric = rubric_name.strip().lower()
    model_name = os.environ.get("OPENAI_MODEL", _DEFAULT_OPENAI_MODEL)
    graph = _create_judge_graph(
        model_name=model_name,
        api_key=_require_openai_api_key(),
        enforce_sub_criterion_ids=normalized_rubric in {"rubric_04", "rubric_05"},
        rubric_name=normalized_rubric,
    )
    result = graph.invoke(
        {
            "attempts": 0,
            "system_prompt": load_judge_prompt(prompt_name=prompt_name, rubric_name=rubric_name),
            "conversation_text": _format_conversation_for_judge(transcript),
            "num_turns": len(exchanges),
        }
    )
    grade_json = result.get("grade_json")
    if grade_json is None:
        raise JudgeError(f"Judge failed to produce valid grade JSON. Last error: {result.get('last_error')}")

    grade_payload = dict(grade_json)
    grade_payload["model"] = {"provider": "openai", "model": model_name, "temperature": 0}
    grade_payload["judge_llm_calls"] = int(result.get("attempts", 0))
    if _env_truthy("JUDGE_INCLUDE_TIMESTAMP"):
        grade_payload["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    grade_payload = _order_grade_payload(grade_payload)

    out_transcript = dict(transcript)
    out_transcript.pop("grade", None)
    out_transcript["grade"] = grade_payload

    output_path = (
        _default_output_path(transcript_path=source_path, prompt_name=prompt_name, rubric_name=rubric_name, provider="gpt")
        if output_name is None
        else source_path.with_name(f"{output_name}.json")
    )
    output_path.write_text(json.dumps(out_transcript, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return JudgeResult(
        total_score=int(grade_payload["total_score"]),
        max_score=int(grade_payload["max_score"]),
        output_path=Path(output_path),
    )


def _discover_raw_transcripts() -> list[Path]:
    return sorted(TRANSCRIPTS_DIR.glob("*/*_raw/transcript_*.json"))


def _provider_target_path(raw_path: Path, provider: str) -> Path:
    persona_dir = raw_path.parent.parent
    persona_type = persona_dir.name
    target_dir = persona_dir / f"{persona_type}_{provider}"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / raw_path.name


def _relative_stem(path: Path) -> str:
    rel = path.relative_to(TRANSCRIPTS_DIR).as_posix()
    return rel[:-5] if rel.endswith(".json") else rel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Grade all raw transcripts with GPT judge into *_gpt folders."
    )
    parser.add_argument("--prompt", default="judge_05", help="Judge prompt stem (default: judge_05).")
    parser.add_argument("--rubric", default="rubric_05", help="Judge rubric stem (default: rubric_05).")
    args = parser.parse_args(argv)

    try:
        _require_openai_api_key()
    except JudgeError as error:
        print(str(error))
        return 1

    raw_files = _discover_raw_transcripts()
    if not raw_files:
        print(f"No raw transcripts found under {TRANSCRIPTS_DIR}")
        return 1

    print(
        f"[GPT Judge] Grading {len(raw_files)} transcripts "
        f"with prompt={args.prompt} rubric={args.rubric}"
    )
    try:
        for raw_path in raw_files:
            target_path = _provider_target_path(raw_path, "gpt")
            shutil.copyfile(raw_path, target_path)
            result = judge_transcript(
                _relative_stem(target_path),
                prompt_name=args.prompt,
                rubric_name=args.rubric,
                output_name=target_path.stem,  # keep transcript_XX.json filename
            )
            print(
                "[GPT Judge] "
                f"source={raw_path.relative_to(_REPO_ROOT)} "
                f"saved={result.output_path.relative_to(_REPO_ROOT)} "
                f"score={result.total_score}/{result.max_score}"
            )
    except KeyboardInterrupt:
        print("\nGPT judging interrupted.")
        return 130
    except JudgeError as error:
        print(f"Judge failed: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
