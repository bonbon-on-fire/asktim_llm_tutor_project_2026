# Judge

LLM-based grader that scores tutor–student conversation transcripts against a rubric.

Current defaults in code:
- prompt: `judge_03`
- rubric: `rubric_04`

## Structure

```
judge/
  __init__.py          — package exports
  run_judge.py         — LangGraph engine, validation, scoring logic
  README.md
  prompts/
    judge_01.txt       — baseline prompt template
    judge_02.txt       — structured prompt template
    judge_03.txt       — current prompt template (context + exercise aware)
  rubrics/
    rubric_01.md       — original rubric profile
    rubric_02.md       — intermediate rubric profile
    rubric_03.md       — prior rubric profile (33 base + 9 bonus = 42 max)
    rubric_04.md       — current rubric profile (47 base with section malus deductions)
```

Transcripts live in the top-level `transcripts/` folder (not inside `judge/`).

## How it works

1. Loads the selected judge system prompt from `prompts/<prompt_name>.txt`, injecting the rubric text from `rubrics/<rubric_name>.md` and the expected JSON schema.
2. Reads a transcript JSON from `transcripts/<name>.json`.
3. Formats the conversation and sends it to the LLM with the system prompt.
4. Parses the LLM's JSON response, sanitizes numeric values, and validates against the schema.
5. If validation fails, sends a repair prompt and retries once (up to 2 attempts total).
6. Writes a `grade` object back into the transcript JSON file.

## Usage

```python
from judge import judge_transcript

result = judge_transcript("chaotic_01_exercise_01_01")
print(result.total_score, result.max_score)  # e.g. 41, 47
```

You can also choose specific judge prompt + rubric versions:

```python
result = judge_transcript(
    "chaotic/transcript_01",
    prompt_name="judge_03",
    rubric_name="rubric_04",
)
```

Alternative profiles:

```python
result = judge_transcript(
    "chaotic/transcript_01",
    prompt_name="judge_02",
    rubric_name="rubric_02",
)
```

## Rubric summary

| Section                  | Sub-criteria | Max points | Catch-all malus |
| :----------------------- | :----------: | ---------: | --------------: |
| 1. Pedagogy              |    1.1–1.3   |         23 |     - |
| 2. Dialogue quality      |    2.1–2.2   |         10 |     - |
| 3. Communication quality |    3.1–3.3   |         14 |     - |
| **Base total**           |              |     **47** |     - |

Section malus deductions (catch-all, only if not already deducted):
- `1.4`: `0..2`
- `2.3`: `0..2`
- `3.4`: `0..2`

Maximum total score: **47**.

## Output contract (current)

- Scores are whole integers only.
- Top-level key order ends with `total_score`, then `judge_llm_calls`.
- `overview` replaces `justifications` and appears near the end.
- Deductions are ordered with `reason` before `points`.
- Each section `malus` requires `explanation`.
- `total_malus` and `max_malus` replace `total_bonus` and `max_bonus`.
- Judge input supports both transcript `context` and `exercise`.

## Environment variables

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `OPENAI_API_KEY` | Yes | OpenAI API key. Fails immediately if not set. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-5.2`). |
| `JUDGE_INCLUDE_TIMESTAMP` | No | If truthy (`1/true/yes/on`), include `timestamp_utc` in grade output. Default off for deterministic artifacts. |

## Claude Re-judge Script

To re-judge existing transcripts with Claude and write outputs into:
- `transcripts/chaotic_claude`
- `transcripts/chitchat_claude`
- `transcripts/clueless_claude`

Run:

```python
python -m judge.run_judge_claude --model claude-sonnet-4-6 --prompt judge_03 --rubric rubric_04
```

Notes:
- The script clears existing `*_claude` transcript JSON files before writing new results.
- Requires `ANTHROPIC_API_KEY` in environment (or `.env`).
