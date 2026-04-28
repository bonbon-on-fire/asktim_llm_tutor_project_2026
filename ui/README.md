# UI Module

Terminal runners for transcript generation and judge scoring with interactive CLI support.

## Available entrypoints

From repo root in PowerShell:

### 1) Generate raw transcripts (no judge)

**Interactive mode (default):**
```powershell
python -m ui.run_ui_raw
```

This will prompt you to select from numbered options:
- **Tutor provider**: `gpt` or `claude` (required)
- **Tutor prompts**: Available from `tutor/prompts/*.txt` (empty input = all)
- **Student personas**: Available from `students/personas/*.txt` (empty input = all)
- **Course/exercise combinations**: Available from `curriculum/` (empty input = all)
- **Turn size**: Number of student+tutor exchanges per conversation
- **Trials**: Number of trials per configuration

**Command-line mode:**
```powershell
# Generate with GPT tutor (default output: *_raw/)
python -m ui.run_ui_raw --provider gpt --tutor tutor_03 --personas clueless_01 chaotic_02 --course philosophy --exercise 01 --turn-size 10 --trials 2

# Generate with Claude tutor
python -m ui.run_ui_raw --provider claude --tutor tutor_05 --personas clueless_01 --course philosophy --exercise 01 --turn-size 10 --trials 2

# Custom output folder: writes to *_raw_tutor_05/ instead of *_raw/ (--yes skips confirmation)
python -m ui.run_ui_raw --provider claude --tutor tutor_05 --personas chaotic_01 --course philosophy --exercise 01 --turn-size 10 --trials 10 --output-suffix raw_tutor_05 --yes
```

Run matrix: `tutor_prompts x student_personas x course_exercises x trials`

**Features:**
- Parallel processing (6 workers by default)
- Thread-safe transcript filename allocation (`transcript_XXXX.json`) during concurrent writes
- Automatic API key validation
- Interactive confirmation before processing

### 2) Mini continuation (pivot a raw transcript, new tutor)

For quick experiments: fork a **raw** transcript at a **pivot turn** `X`, keep full student+tutor for turns `1 .. X-1`, keep **only** the saved **student** line for turn `X`, then run the **new tutor** first (regenerating the tutor side of turn `X`). After that, append more full student+tutor exchanges. The student model stays **OpenAI** (same as `run_student`); you choose the **tutor** provider (`gpt` or `claude`) for continuation.

**Interactive (recommended):**
```powershell
python -m ui.run_ui_raw_mini
```

**Command-line** (same flags as the tutor module; `ui.run_ui_raw_mini` forwards any arguments):
```powershell
python -m tutor.run_tutor_mini --persona-type chaotic --transcript transcript_01 --resume-from-turn 5 --additional-turns 3 --tutor-prompt tutor_04 --tutor-provider gpt
```

**Options (`tutor.run_tutor_mini`):**
- `--persona-type`: Folder under `transcripts/` (`chaotic`, `chitchat`, `clueless`, `cooperative`)
- `--transcript`: Stem in the persona’s `*_raw` folder (e.g. `transcript_01`)
- `--resume-from-turn`: Pivot `X` — full history through turn `X-1`; turn `X` uses file student text only, then tutor replies first
- `--additional-turns`: Count of **full** student+tutor exchanges **after** that new tutor reply (`0` = only regenerate tutor at turn `X`)
- `--tutor-prompt`, `--tutor-provider`: Tutor prompt stem and `gpt` or `claude` for continuation

**Output:** `transcripts/<type>/<type>_mini/transcript_XXXX.json`. Saved JSON includes `mini_continuation` (source path, `resume_from_turn`, `additional_turns`, original tutor fields).

### 3) Two-layer raw transcripts (rubric-aware verifier)

Same workflow as `run_ui_raw` but uses the two-layer tutor. Each turn first generates a draft reply; a rubric-aware verifier inspects the student-facing text and may request one retry per turn.

**Interactive (recommended):**
```powershell
python -m ui.run_ui_raw_two_layer
```

**Command-line mode:**
```powershell
python -m ui.run_ui_raw_two_layer --provider gpt --tutor tutor_05 --rubric rubric_05 --personas clueless_01 --course philosophy --exercise 01 --turn-size 10 --trials 2
```

Prompts for the same options as `run_ui_raw` plus a **rubric** selection (used by the verifier layer only — the tutor itself has no rubric access).

**Output:** `transcripts/<type>/<type>_two_layer_raw/transcript_XXXX.json`.
Each exchange includes a `verifier` field: `{"retried": false}` when the first draft was approved, or `{"retried": true, "feedback": "..."}` when a retry was requested.

### 4) Comparison mini judge (new vs original tutor reply)

For quick prompt evaluation: randomly samples pivot turns from raw transcripts, regenerates the tutor reply with the current prompt, and asks the mini judge whether the new reply is better.

**Interactive (recommended):**
```powershell
python -m ui.run_ui_judge_mini
```

Prompts for:
- **Number of samples** to run
- **Tutor provider** (`gpt` or `claude`)
- **Tutor prompt** (from `tutor/prompts/`)
- **Judge rubric** (from `judge/rubrics/`)
- **Judge provider** (`gpt` or `claude`)

Output is printed to the terminal in three sections:
1. All student messages + both tutor replies (original and new)
2. Per-sample YES/NO verdict with a one-sentence reason
3. Summary stats (% of samples where new reply was judged better)

### 5) Judge raw transcripts (GPT or Claude)

**Interactive mode (default):**
```powershell
python -m ui.run_ui_judge
```

This will prompt you to select from numbered options:
- **Judge provider**: gpt or claude (required)
- **Judge prompt**: Available from `judge/prompts/judge_*.txt` (required)
- **Judge rubric**: Available from `judge/rubrics/rubric_*.md` (required)

**Command-line mode:**
```powershell
# Grade with GPT (reads *_raw/, writes *_gpt/)
python -m ui.run_ui_judge --provider gpt --prompt judge_05 --rubric rubric_05

# Grade with Claude (reads *_raw/, writes *_claude/)
python -m ui.run_ui_judge --provider claude --prompt judge_05 --rubric rubric_05

# Read from *_raw_tutor_05/, write to *_claude_tutor_05/ (--yes skips confirmation)
python -m ui.run_ui_judge --provider claude --prompt judge_05 --rubric rubric_05 \
  --source-suffix raw_tutor_05 --output-suffix tutor_05 --yes

# Read from *_mini/, write to *_claude_mini/
python -m ui.run_ui_judge --provider claude --prompt judge_05 --rubric rubric_05 \
  --source-suffix mini --output-suffix mini --yes
```

The script discovers all transcripts matching `*_{source-suffix}/transcript_*.json`, copies each to the provider+suffix-specific folder, then applies judging in-place.

**Features:**
- Parallel processing (6 workers by default)
- Progress tracking with section scores
- Automatic API key validation per provider
- Overwrites existing graded files with warning
- Interactive confirmation before processing

## Output paths

### Raw-only runs (`ui.run_ui_raw`)

Raw transcripts are saved to persona-specific raw folders:

- `transcripts/chaotic/chaotic_raw/`
- `transcripts/clueless/clueless_raw/`
- `transcripts/cooperative/cooperative_raw/`

With `--output-suffix raw_tutor_05`, output goes to `*_raw_tutor_05/` instead:

- `transcripts/chaotic/chaotic_raw_tutor_05/`
- `transcripts/clueless/clueless_raw_tutor_05/`
- `transcripts/cooperative/cooperative_raw_tutor_05/`

Each file is auto-named as `transcript_XXXX.json`.

### Judged runs (`ui.run_ui_judge`)

Judged transcripts are saved to provider-specific folders:

**GPT judged:**
- `transcripts/chaotic/chaotic_gpt/`
- `transcripts/clueless/clueless_gpt/`
- `transcripts/cooperative/cooperative_gpt/`

**Claude judged (default):**
- `transcripts/chaotic/chaotic_claude/`
- `transcripts/clueless/clueless_claude/`
- `transcripts/cooperative/cooperative_claude/`

**Claude judged with custom suffix** (`--source-suffix raw_tutor_05 --output-suffix tutor_05`):
- `transcripts/chaotic/chaotic_claude_tutor_05/`
- `transcripts/clueless/clueless_claude_tutor_05/`
- `transcripts/cooperative/cooperative_claude_tutor_05/`

**Claude judged mini** (`--source-suffix mini --output-suffix mini`):
- `transcripts/chaotic/chaotic_claude_mini/`
- `transcripts/clueless/clueless_claude_mini/`

Each output file uses the same stem as the source input: `transcript_XXXX.json`

### Mini continuation outputs (`ui.run_ui_raw_mini` / `tutor.run_tutor_mini`)

- `transcripts/chaotic/chaotic_mini/`
- `transcripts/clueless/clueless_mini/`

Output file is named using the same stem as the source raw transcript.

### Two-layer raw outputs (`ui.run_ui_raw_two_layer`)

- `transcripts/chaotic/chaotic_two_layer_raw/`
- `transcripts/clueless/clueless_two_layer_raw/`
- `transcripts/cooperative/cooperative_two_layer_raw/`

## Transcript schema (core fields)

All transcript flows include run metadata and exchanges:

```json
{
  "tutor_provider": "gpt",
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

Mini continuation outputs additionally include:

- `student_provider`: `gpt` (student stack is always OpenAI here)
- `mini_continuation` (object): `source_transcript`, `source_stem`, `resume_from_turn`, `additional_turns`, `original_tutor_prompt`, `original_tutor_provider`

Two-layer raw outputs additionally include:

- `verifier_rubric`: rubric name used by the verifier (e.g. `rubric_05`)
- Per exchange: `verifier` field — `{"retried": false}` if the first draft was approved, or `{"retried": true, "feedback": "..."}` if a retry was requested

## Interactive CLI Features

`run_ui_raw`, `run_ui_raw_two_layer`, `run_ui_judge`, and related runners support both interactive and command-line modes. **`run_ui_raw_mini`** is interactive when run with **no** arguments; with arguments it delegates to **`tutor.run_tutor_mini`** (same parser as `python -m tutor.run_tutor_mini`). **`run_ui_judge_mini`** is always interactive.

- **Interactive mode**: Run without arguments to get numbered selection prompts
- **Command-line mode**: Provide all required arguments to skip prompts
- **Smart defaults**: `run_ui_raw` allows empty input (defaults to "all available")
- **Required inputs**: Judge scripts require explicit selection of all options
- **Confirmation**: Interactive mode shows summary and asks for confirmation
- **Range support**: Select multiple items with ranges like `1-5` or `1,3,5-7`

## Parallelism configuration

- `ui.run_ui_raw` and `ui.run_ui_judge` both run with `6` workers by default.
- Adjust `PARALLEL_WORKERS` at the top of each runner file to change concurrency.

## Environment variables

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `OPENAI_API_KEY` | For GPT | OpenAI API key. Required when using GPT as tutor or judge provider. |
| `OPENAI_MODEL` | No | OpenAI model name (default: `gpt-5.4`). |
| `ANTHROPIC_API_KEY` | For Claude | Anthropic API key. Required when using Claude as tutor or judge provider. |
| `ANTHROPIC_MODEL` | No | Anthropic model name for Claude tutor or judge (default: `claude-sonnet-4-6`). |
