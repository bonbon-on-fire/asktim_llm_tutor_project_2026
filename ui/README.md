# UI Module

Terminal runner tools for tutor/student simulation and judge scoring.

## How to run

### Interactive run (sim + judge)

```powershell
python -m ui
```

This launches the prompt-based flow:

| Step | Prompt | Source |
| ---- | ------ | ------ |
| 0 | Tutor prompt version | Scans `tutor/prompts/*.txt` |
| 1 | Student persona type | `chaotic`, `chitchat`, `clueless` |
| 2 | Student persona version | Scans `students/personas/{type}_*.txt` |
| 3 | Course | Scans `curriculum/` subfolder names |
| 4 | Exercise number | Scans `curriculum/{course}/exercise_*.txt` |
| 5 | Number of turns | Positive integer |
| 6 | Judge prompt version | Scans `judge/prompts/*.txt` |
| 7 | Judge rubric version | Scans `judge/rubrics/*.md` |
| 8 | Run, save transcript, and judge | See output sections below |

### Batch run (sim + judge)

```powershell
python -m ui.run_batch
```

Before running, edit these constants in `ui/run_batch.py`:

- `TUTOR_PROMPTS`
- `STUDENT_PERSONAS`
- `COURSE_EXERCISES` (as `(course, exercise_number)` tuples)
- `JUDGE_PROMPTS`
- `JUDGE_RUBRICS`
- `TRIALS`
- `TURN_SIZE`

Run matrix:

`tutor_prompts x student_personas x course_exercises x judge_prompts x judge_rubrics x trials`

### Batch run (raw transcripts only, no judge)

```powershell
python -m ui.run_ui_raw
```

Before running, edit these constants in `ui/run_ui_raw.py`:

- `TUTOR_PROMPTS`
- `STUDENT_PERSONAS`
- `COURSE_EXERCISES` (as `(course, exercise_number)` tuples)
- `TRIALS`
- `TURN_SIZE`

Run matrix:

`tutor_prompts x student_personas x course_exercises x trials`

### Batch run (judge raw transcripts with GPT)

```powershell
python -m ui.run_ui_gpt
```

Before running, edit these constants in `ui/run_ui_gpt.py`:

- `JUDGE_PROMPTS`
- `JUDGE_RUBRICS`
- `STUDENT_PERSONAS`
- `RAW_TRANSCRIPTS` (optional explicit transcript stems per persona type; empty means auto-discover all)

The script reads from `*_raw` folders, copies each selected transcript to `*_gpt`, then applies GPT judging in-place on the copied file.

### Batch run (judge raw transcripts with Claude)

```powershell
python -m ui.run_ui_claude
```

Before running, edit these constants in `ui/run_ui_claude.py`:

- `JUDGE_PROMPTS`
- `JUDGE_RUBRICS`
- `STUDENT_PERSONAS`
- `RAW_TRANSCRIPTS` (optional explicit transcript stems per persona type; empty means auto-discover all)

The script reads from `*_raw` folders, copies each selected transcript to `*_claude`, then applies Claude judging in-place on the copied file.

## Output paths

### Judged runs (`ui` and `ui.run_batch`)

Transcripts are saved under:

- `transcripts/{persona_type}/transcript_XX.json`

Judge output is appended into each transcript under `grade`.

Compiled CSV summary is appended to:

- `transcripts/transcripts_compiled.csv`

### Raw-only runs (`ui.run_ui_raw`)

Raw transcripts are saved to persona-specific raw folders:

- `transcripts/chaotic/chaotic_raw/`
- `transcripts/chitchat/chitchat_raw/`
- `transcripts/clueless/clueless_raw/`

Each file is auto-named as `transcript_XX.json`.

### GPT judged runs (`ui.run_ui_gpt`)

Judged transcripts are saved to:

- `transcripts/chaotic/chaotic_gpt/`
- `transcripts/chitchat/chitchat_gpt/`
- `transcripts/clueless/clueless_gpt/`

Each output file uses:

- `{raw_stem}__{judge_prompt}__{judge_rubric}.json`

### Claude judged runs (`ui.run_ui_claude`)

Judged transcripts are saved to:

- `transcripts/chaotic/chaotic_claude/`
- `transcripts/chitchat/chitchat_claude/`
- `transcripts/clueless/clueless_claude/`

Each output file uses:

- `{raw_stem}__{judge_prompt}__{judge_rubric}.json`

## Transcript schema (core fields)

All transcript flows include run metadata and exchanges:

```json
{
  "tutor_prompt": "tutor_01",
  "student_persona": "chaotic_01",
  "course": "philosophy",
  "exercise_number": "01",
  "turn_size": 10,
  "context": "Course-level context loaded from curriculum/<course>/course.txt",
  "exercise": "Combined assignment text (course context + exercise + run configuration)...",
  "turns": 10,
  "exchanges": [
    {
      "turn": 1,
      "student": "...",
      "tutor": "...",
      "pedagogical_reasoning": "Tutor reasoning for this turn"
    }
  ]
}
```

Judged flows additionally include:

- `judge_prompt`
- `judge_rubric`
- `grade`

## Environment variables

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `OPENAI_API_KEY` | Yes | OpenAI API key. Fails immediately if not set. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-5.2`). |
| `ANTHROPIC_API_KEY` | For Claude judge | Anthropic API key required by `ui.run_ui_claude`. |
| `ANTHROPIC_MODEL` | No | Model name for Claude judge (default: `claude-sonnet-4-6`). |
