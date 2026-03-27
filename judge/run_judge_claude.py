"""Claude-based judge for humanities tutor transcripts."""

from __future__ import annotations

import ast
import argparse
import json
import os
import re
import shutil
import sys
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

warnings.filterwarnings(
    "ignore",
    message=r"Core Pydantic V1 functionality isn't compatible with Python 3\.14 or greater\.",
    category=UserWarning,
)

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import NotRequired, TypedDict
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
load_dotenv(_REPO_ROOT / ".env")

from utils.parsing import extract_json_object

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
RUBRICS_DIR = Path(__file__).resolve().parent / "rubrics"
TRANSCRIPTS_DIR = _REPO_ROOT / "transcripts"

_DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
_MAX_ATTEMPTS = 3

_RUBRIC_SPECS: dict[str, dict[str, Any]] = {
    "rubric_04": {
        "provider": "claude",
        "max_base_score": 47,
        "max_score": 47,
        "criterion_max": {
            "1.1": 12,
            "1.2": 6,
            "1.3": 5,
            "2.1": 4,
            "2.2": 6,
            "3.1": 6,
            "3.2": 5,
            "3.3": 3,
        },
        "criterion_names": {
            "1.1": "Socratic method and guided discovery",
            "1.2": "Scaffolding and progression",
            "1.3": "Meta-learning and methodology feedback",
            "2.1": "Redundancy and spiraling",
            "2.2": "Assignment anchoring",
            "3.1": "Bite-sized and clear responses",
            "3.2": "Appropriate tone and support",
            "3.3": "Formatting and medium",
        },
        "sections": {
            "1_pedagogy": {"criteria": ["1.1", "1.2", "1.3"], "malus_id": "1.4"},
            "2_dialogue_quality": {"criteria": ["2.1", "2.2"], "malus_id": "2.3"},
            "3_communication_quality": {"criteria": ["3.1", "3.2", "3.3"], "malus_id": "3.4"},
        },
        "malus_max": 2,
    },
    "rubric_05": {
        "provider": "claude",
        "max_base_score": 46,
        "max_score": 46,
        "criterion_max": {
            "1.1": 12,
            "1.2": 6,
            "1.3": 6,
            "2.1": 4,
            "2.2": 8,
            "3.1": 6,
            "3.2": 4,
        },
        "criterion_names": {
            "1.1": "Socratic method and guided discovery",
            "1.2": "Scaffolding and progression",
            "1.3": "Meta-learning and methodology feedback",
            "2.1": "Redundancy and spiraling",
            "2.2": "Assignment anchoring",
            "3.1": "Bite-sized and clear responses",
            "3.2": "Appropriate tone and support",
        },
        "sections": {
            "1_pedagogy": {"criteria": ["1.1", "1.2", "1.3"], "malus_id": None},
            "2_dialogue_quality": {"criteria": ["2.1", "2.2"], "malus_id": None},
            "3_communication_quality": {"criteria": ["3.1", "3.2"], "malus_id": None},
        },
        "malus_max": 0,
    },
}


class JudgeError(RuntimeError):
    """Raised when transcript judging fails."""


@dataclass(slots=True)
class JudgeResult:
    total_score: int
    max_score: int
    output_path: Path


class _JudgeState(TypedDict):
    attempts: int
    system_prompt: str
    conversation_text: str
    num_turns: int
    last_output: NotRequired[str]
    last_error: NotRequired[str]
    grade_json: NotRequired[dict[str, Any]]


def _coerce_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            if "." in text:
                return int(round(float(text)))
            return int(text)
        except ValueError:
            return default
    return default


def _clamp_int(value: Any, *, minimum: int, maximum: int) -> int:
    parsed = _coerce_int(value, default=minimum)
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed


def _sanitize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for k, v in value.items():
            normalized[str(k)] = _normalize_json_value(v)
        return normalized
    if isinstance(value, (list, tuple, set)):
        return [_normalize_json_value(v) for v in value]
    return str(value)


def _env_truthy(name: str) -> bool:
    raw = os.environ.get(name, "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _require_anthropic_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise JudgeError("ANTHROPIC_API_KEY environment variable is required but not set.")
    return key


def _fenced_json(text: str) -> str | None:
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    return match.group(1).strip() if match else None


def _extract_text_from_model_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
                    continue
            text_attr = getattr(item, "text", None)
            if isinstance(text_attr, str):
                chunks.append(text_attr)
                continue
            chunks.append(str(item))
        return "\n".join(chunks)
    return str(content)


def _parse_json_from_model_output(output_text: str) -> dict[str, Any]:
    text = _sanitize_text(output_text).strip()
    candidates = [text, _fenced_json(text), extract_json_object(text)]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return _normalize_json_value(parsed)
        except json.JSONDecodeError:
            continue

    extracted = extract_json_object(text)
    if extracted:
        try:
            literal = ast.literal_eval(extracted)
            literal = _normalize_json_value(literal)
            if isinstance(literal, dict):
                return literal
        except (SyntaxError, ValueError):
            pass

    raise JudgeError("Judge response does not contain a valid JSON object.")


def _normalize_deduction(item: Any, *, enforce_sub_criterion_ids: bool) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}
    evidence_raw = item.get("evidence_turns")
    evidence: list[int] = []
    if isinstance(evidence_raw, list):
        for v in evidence_raw:
            n = _coerce_int(v, default=0)
            if n > 0:
                evidence.append(n)
    elif evidence_raw is not None:
        n = _coerce_int(evidence_raw, default=0)
        if n > 0:
            evidence.append(n)

    sub_criterion_id = _sanitize_text(item.get("sub_criterion_id")).strip()
    if enforce_sub_criterion_ids and not sub_criterion_id:
        sub_criterion_id = "missing"

    deduction: dict[str, Any] = {}
    if evidence:
        deduction["evidence_turns"] = evidence
    if sub_criterion_id:
        deduction["sub_criterion_id"] = sub_criterion_id
    deduction["reason"] = _sanitize_text(item.get("reason")).strip()
    deduction["points"] = max(0, _coerce_int(item.get("points"), default=0))
    return deduction


def _sanitize_grade_payload(payload: dict[str, Any]) -> dict[str, Any]:
    payload = _normalize_json_value(payload)
    if not isinstance(payload, dict):
        raise JudgeError("Grade payload must be a JSON object.")
    if "sections" not in payload or not isinstance(payload.get("sections"), dict):
        payload["sections"] = {}
    if "overview" not in payload:
        summary = payload.get("summary")
        if isinstance(summary, list):
            payload["overview"] = summary
        else:
            payload["overview"] = []
    if not isinstance(payload.get("overview"), list):
        payload["overview"] = [str(payload["overview"])]
    payload["overview"] = [_sanitize_text(v) for v in payload["overview"]]
    return payload


def _rubric_spec(rubric_name: str) -> dict[str, Any]:
    key = rubric_name.strip().lower()
    if key not in _RUBRIC_SPECS:
        available = ", ".join(sorted(_RUBRIC_SPECS.keys()))
        raise JudgeError(f"Unsupported rubric '{rubric_name}'. Available: {available}")
    return _RUBRIC_SPECS[key]


def _validate_grade_payload(
    payload: dict[str, Any],
    *,
    num_turns: int,
    enforce_sub_criterion_ids: bool,
    rubric_name: str,
) -> dict[str, Any]:
    del num_turns  # reserved for future strict evidence_turn checks
    spec = _rubric_spec(rubric_name)
    sections_in = payload.get("sections")
    if not isinstance(sections_in, dict):
        raise JudgeError("Grade payload must include an object at 'sections'.")

    normalized_sections: dict[str, Any] = {}
    criterion_max = spec["criterion_max"]
    criterion_names = spec["criterion_names"]

    for section_id, section_spec in spec["sections"].items():
        section_in = sections_in.get(section_id)
        if not isinstance(section_in, dict):
            section_in = {}
        criteria_in = section_in.get("criteria")
        if not isinstance(criteria_in, dict):
            criteria_in = {}

        section_criteria: dict[str, Any] = {}
        section_score = 0
        section_max = 0

        for criterion_id in section_spec["criteria"]:
            criterion_in = criteria_in.get(criterion_id)
            if not isinstance(criterion_in, dict):
                criterion_in = {}
            deductions_in = criterion_in.get("deductions")
            if not isinstance(deductions_in, list):
                deductions_in = []

            max_points = int(criterion_max[criterion_id])
            deductions = [
                _normalize_deduction(d, enforce_sub_criterion_ids=enforce_sub_criterion_ids)
                for d in deductions_in
            ]
            deducted = sum(_coerce_int(d.get("points"), default=0) for d in deductions)
            score = max(0, min(max_points, max_points - deducted))

            section_criteria[criterion_id] = {
                "deductions": deductions,
                "score": score,
                "max": max_points,
                "name": criterion_names.get(criterion_id, criterion_id),
            }
            section_score += score
            section_max += max_points

        section_payload: dict[str, Any] = {
            "criteria": section_criteria,
            "base": {"score": section_score, "max": section_max},
        }

        malus_id = section_spec.get("malus_id")
        if malus_id:
            malus_in = section_in.get("malus")
            if not isinstance(malus_in, dict):
                malus_in = {}
            malus_score = _clamp_int(malus_in.get("score"), minimum=0, maximum=int(spec["malus_max"]))
            section_payload["malus"] = {
                "id": _sanitize_text(malus_in.get("id")).strip() or malus_id,
                "explanation": _sanitize_text(malus_in.get("explanation")).strip(),
                "score": malus_score,
                "max": int(spec["malus_max"]),
            }

        normalized_sections[section_id] = section_payload

    total_base_score = sum(
        int(section["base"]["score"]) for section in normalized_sections.values()
    )
    max_base_score = int(spec["max_base_score"])

    out: dict[str, Any] = {
        "sections": normalized_sections,
        "max_score": int(spec["max_score"]),
        "total_base_score": total_base_score,
        "max_base_score": max_base_score,
    }

    if int(spec["malus_max"]) > 0:
        total_malus = sum(
            int(section.get("malus", {}).get("score", 0)) for section in normalized_sections.values()
        )
        max_malus = int(spec["malus_max"]) * len(spec["sections"])
        out["total_malus"] = total_malus
        out["max_malus"] = max_malus
        out["total_score"] = max(0, total_base_score - total_malus)
    else:
        out["total_score"] = total_base_score

    out["overview"] = payload.get("overview", [])
    if not isinstance(out["overview"], list):
        out["overview"] = [str(out["overview"])]
    out["overview"] = [_sanitize_text(v) for v in out["overview"]]
    out["judge_llm_calls"] = _coerce_int(payload.get("judge_llm_calls"), default=1)
    return out


def _order_grade_payload(payload: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {"sections": payload["sections"]}
    for key in ("max_score", "total_base_score", "max_base_score"):
        if key in payload:
            ordered[key] = payload[key]
    for key in ("total_malus", "max_malus"):
        if key in payload:
            ordered[key] = payload[key]
    for key in ("id", "summary", "type", "model", "timestamp_utc"):
        if key in payload:
            ordered[key] = payload[key]
    ordered["overview"] = payload.get("overview", [])
    ordered["total_score"] = payload["total_score"]
    ordered["judge_llm_calls"] = payload.get("judge_llm_calls", 1)
    return ordered


def _grade_schema_for_prompt(rubric_name: str) -> dict[str, Any]:
    spec = _rubric_spec(rubric_name)
    sections: dict[str, Any] = {}
    for section_id, section_spec in spec["sections"].items():
        criteria: dict[str, Any] = {}
        for criterion_id in section_spec["criteria"]:
            criteria[criterion_id] = {
                "deductions": [
                    {
                        "evidence_turns": [1, 2],
                        "sub_criterion_id": f"{criterion_id}.A.a",
                        "reason": "Short evidence-based deduction reason.",
                        "points": 1,
                    }
                ],
                "score": spec["criterion_max"][criterion_id],
                "max": spec["criterion_max"][criterion_id],
                "name": spec["criterion_names"][criterion_id],
            }
        section_payload: dict[str, Any] = {
            "criteria": criteria,
            "base": {
                "score": sum(spec["criterion_max"][c] for c in section_spec["criteria"]),
                "max": sum(spec["criterion_max"][c] for c in section_spec["criteria"]),
            },
        }
        if section_spec.get("malus_id"):
            section_payload["malus"] = {
                "id": section_spec["malus_id"],
                "explanation": "",
                "score": 0,
                "max": spec["malus_max"],
            }
        sections[section_id] = section_payload

    payload: dict[str, Any] = {
        "sections": sections,
        "max_score": spec["max_score"],
        "total_base_score": spec["max_base_score"],
        "max_base_score": spec["max_base_score"],
    }
    if spec["malus_max"] > 0:
        payload["total_malus"] = 0
        payload["max_malus"] = spec["malus_max"] * len(spec["sections"])
    payload["overview"] = ["Brief evidence-based overview."]
    payload["total_score"] = spec["max_score"]
    payload["judge_llm_calls"] = 1
    return payload


def load_judge_prompt(*, prompt_name: str = "judge_05", rubric_name: str = "rubric_05") -> str:
    prompt_path = PROMPTS_DIR / f"{prompt_name}.txt"
    rubric_path = RUBRICS_DIR / f"{rubric_name}.md"
    if not prompt_path.exists():
        available = sorted(p.stem for p in PROMPTS_DIR.glob("*.txt"))
        raise JudgeError(f"Judge prompt '{prompt_name}' not found. Available: {available}")
    if not rubric_path.exists():
        available = sorted(p.stem for p in RUBRICS_DIR.glob("*.md"))
        raise JudgeError(f"Judge rubric '{rubric_name}' not found. Available: {available}")

    prompt_template = prompt_path.read_text(encoding="utf-8")
    rubric_text = rubric_path.read_text(encoding="utf-8")
    schema_text = json.dumps(_grade_schema_for_prompt(rubric_name), ensure_ascii=False, indent=2)
    return prompt_template.format(rubric=rubric_text.strip(), schema=schema_text).strip()


def _format_conversation_for_judge(transcript: dict[str, Any]) -> str:
    lines: list[str] = []
    context = _sanitize_text(transcript.get("context")).strip()
    exercise = _sanitize_text(transcript.get("exercise")).strip()
    if context:
        lines.append("CONTEXT:")
        lines.append(context)
        lines.append("")
    if exercise:
        lines.append("EXERCISE:")
        lines.append(exercise)
        lines.append("")

    lines.append("TRANSCRIPT:")
    exchanges = transcript.get("exchanges")
    if not isinstance(exchanges, list):
        exchanges = []
    for i, exchange in enumerate(exchanges, start=1):
        if not isinstance(exchange, dict):
            continue
        turn = _coerce_int(exchange.get("turn"), default=i)
        student = _sanitize_text(exchange.get("student")).strip()
        tutor = _sanitize_text(exchange.get("tutor")).strip()
        lines.append(f"Turn {turn}")
        lines.append(f"Student: {student}")
        lines.append(f"Tutor: {tutor}")
        lines.append("")

    return "\n".join(lines).strip()


def _judge_repair_prompt(last_error: str) -> str:
    return (
        "Your previous response could not be validated as the required grade JSON.\n"
        f"Validation error: {last_error}\n"
        "Return ONLY corrected JSON that matches the expected schema exactly."
    )


def _create_judge_graph(*, model_name: str, api_key: str, enforce_sub_criterion_ids: bool, rubric_name: str):
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


def _default_output_path(*, transcript_path: Path, prompt_name: str, rubric_name: str, provider: str) -> Path:
    stem = transcript_path.stem
    filename = f"{stem}__{prompt_name}__{rubric_name}__{provider}.json"
    return transcript_path.with_name(filename)


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
    model_name = os.environ.get("ANTHROPIC_MODEL", _DEFAULT_ANTHROPIC_MODEL)
    graph = _create_judge_graph(
        model_name=model_name,
        api_key=_require_anthropic_api_key(),
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
    grade_payload["model"] = {"provider": "anthropic", "model": model_name, "temperature": 0}
    grade_payload["judge_llm_calls"] = int(result.get("attempts", 0))
    if _env_truthy("JUDGE_INCLUDE_TIMESTAMP"):
        grade_payload["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    grade_payload = _order_grade_payload(grade_payload)

    out_transcript = dict(transcript)
    out_transcript.pop("grade", None)
    out_transcript["grade"] = grade_payload

    output_path = (
        _default_output_path(transcript_path=source_path, prompt_name=prompt_name, rubric_name=rubric_name, provider="claude")
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
        description="Grade all raw transcripts with Claude judge into *_claude folders."
    )
    parser.add_argument("--prompt", default="judge_05", help="Judge prompt stem (default: judge_05).")
    parser.add_argument("--rubric", default="rubric_05", help="Judge rubric stem (default: rubric_05).")
    args = parser.parse_args(argv)

    try:
        _require_anthropic_api_key()
    except JudgeError as error:
        print(str(error))
        return 1

    raw_files = _discover_raw_transcripts()
    if not raw_files:
        print(f"No raw transcripts found under {TRANSCRIPTS_DIR}")
        return 1

    print(
        f"[Claude Judge] Grading {len(raw_files)} transcripts "
        f"with prompt={args.prompt} rubric={args.rubric}"
    )
    try:
        for raw_path in raw_files:
            target_path = _provider_target_path(raw_path, "claude")
            shutil.copyfile(raw_path, target_path)
            result = judge_transcript(
                _relative_stem(target_path),
                prompt_name=args.prompt,
                rubric_name=args.rubric,
                output_name=target_path.stem,  # keep transcript_XX.json filename
            )
            print(
                "[Claude Judge] "
                f"source={raw_path.relative_to(_REPO_ROOT)} "
                f"saved={result.output_path.relative_to(_REPO_ROOT)} "
                f"score={result.total_score}/{result.max_score}"
            )
    except KeyboardInterrupt:
        print("\nClaude judging interrupted.")
        return 130
    except JudgeError as error:
        print(f"Judge failed: {error}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
