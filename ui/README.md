# UI Module

Terminal runners for transcript generation and judge scoring.

## Available entrypoints

From repo root in PowerShell:

### 1) Generate raw transcripts (no judge)

```powershell
python -m ui.run_ui_raw
```

Edit config in `ui/run_ui_raw.py`:

- `TUTOR_PROMPTS`
- `STUDENT_PERSONAS`
- `COURSE_EXERCISES` (as `(course, exercise_number)` tuples)
- `TRIALS`
- `TURN_SIZE`

Run matrix:

`tutor_prompts x student_personas x course_exercises x trials`

### 2) Judge raw transcripts (GPT or Claude)

```powershell
# Grade with GPT
python -m ui.run_ui_judge --provider gpt

# Grade with Claude  
python -m ui.run_ui_judge --provider claude

# Custom prompt/rubric
python -m ui.run_ui_judge --provider gpt --prompt judge_06 --rubric rubric_06
```

The script automatically discovers all raw transcripts in `*_raw` folders, copies each to the provider-specific folder (`*_gpt` or `*_claude`), then applies judging in-place on the copied file.

**Options:**
- `--provider {gpt,claude}` (required): Choose judge provider
- `--prompt PROMPT`: Judge prompt stem (default: judge_05)
- `--rubric RUBRIC`: Judge rubric stem (default: rubric_05)

**Features:**
- Parallel processing (6 workers by default)
- Progress tracking with section scores
- Automatic API key validation per provider
- Overwrites existing graded files with warning

## Output paths

### Raw-only runs (`ui.run_ui_raw`)

Raw transcripts are saved to persona-specific raw folders:

- `transcripts/chaotic/chaotic_raw/`
- `transcripts/chitchat/chitchat_raw/`
- `transcripts/clueless/clueless_raw/`

Each file is auto-named as `transcript_XX.json`.

### Judged runs (`ui.run_ui_judge`)

Judged transcripts are saved to provider-specific folders:

**GPT judged:**
- `transcripts/chaotic/chaotic_gpt/`
- `transcripts/chitchat/chitchat_gpt/`
- `transcripts/clueless/clueless_gpt/`

**Claude judged:**
- `transcripts/chaotic/chaotic_claude/`
- `transcripts/chitchat/chitchat_claude/`
- `transcripts/clueless/clueless_claude/`

Each output file uses the same stem as raw input: `transcript_XX.json`

## Transcript schema (core fields)

All transcript flows include run metadata and exchanges:

```json
{
  "tutor_prompt": "tutor_03",
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

Judged transcripts additionally include:

- `judge_prompt`
- `judge_rubric`
- `grade`

## Environment variables

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `OPENAI_API_KEY` | Yes | OpenAI API key. Fails immediately if not set. |
| `OPENAI_MODEL` | No | Model name (default: `gpt-5.4`). |
| `ANTHROPIC_API_KEY` | For Claude judge | Anthropic API key required by `ui.run_ui_claude`. |
| `ANTHROPIC_MODEL` | No | Model name for Claude judge (default: `claude-sonnet-4-6`). |
