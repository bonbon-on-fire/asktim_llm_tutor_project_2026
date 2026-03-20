# Transcripts UI

Flask app to browse judged tutor transcripts and compare GPT vs Claude grades.

## Run

From repo root in PowerShell:

```powershell
python -m flask --app transcripts_ui.run_transcripts_ui run -p 5001
```

Or:

```powershell
python -m transcripts_ui.run_transcripts_ui
```

Then open [http://127.0.0.1:5001](http://127.0.0.1:5001).

## Data source

- By default, the app reads from `transcripts/` in repo root.
- Override with env var `TRANSCRIPTS_DIR` if needed.
- Expected judged inputs (raw is intentionally ignored):
  - `transcripts/chaotic/chaotic_gpt/*.json`
  - `transcripts/chaotic/chaotic_claude/*.json`
  - `transcripts/chitchat/chitchat_gpt/*.json`
  - `transcripts/chitchat/chitchat_claude/*.json`
  - `transcripts/clueless/clueless_gpt/*.json`
  - `transcripts/clueless/clueless_claude/*.json`

The app pairs GPT and Claude files by full transcript stem (for example `transcript_09__judge_03__rubric_04`).

## Features

- Dashboard with GPT/Claude score distributions.
- Sortable transcript table with side-by-side total scores.
- Transcript reader with metadata, exchanges, and both evaluator reports.
