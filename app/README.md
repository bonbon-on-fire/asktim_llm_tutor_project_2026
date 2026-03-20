# Transcript Viewer

Flask app to navigate and read tutor–student transcripts with GPT and Claude evaluation grades.

## Run

From repo root in PowerShell:

```powershell
python -m flask --app app.app run -p 5001
```

Or:

```powershell
python .\app\app.py
```

Then open [http://127.0.0.1:5001](http://127.0.0.1:5001).

## Data source

- By default, the app reads from `transcripts/` in repo root.
- Override with env var `TRANSCRIPTS_DIR` if needed.
- Current server code expects:
  - base transcripts in `transcripts/<persona>/transcript_XX.json`
  - Claude companion files in `transcripts/<persona>_claude/transcript_XX.json`

## Features

- **Dashboard**: Grade distribution charts (GPT and Claude evaluators) and a sortable table of all conversations.
- **Transcript reader**: Read full conversation with metadata, exchanges (student, tutor, pedagogical reasoning), and both grade reports at the end.
