# Visualization

Generate score comparison charts for GPT vs Claude transcript grading.

## Inputs

Reads judged transcript JSON files from:

- `transcripts/<persona_type>/<persona_type>_gpt/transcript_*.json`
- `transcripts/<persona_type>/<persona_type>_claude/transcript_*.json`

Required JSON fields per file:

- `tutor_prompt`, `student_persona`, `course`, `exercise_number`
- `grade.total_score`, `grade.max_score`

`transcript_name` is derived from each file name (e.g. `transcript_01`).

## Run

```powershell
python -m visualization.run_visualization
```

## Outputs

Written to `visualization/outputs/`:

- **`individual_grades_gpt_vs_claude.png`**
  Line chart of total scores per transcript (individual judging), sorted by
  persona/course/exercise. Includes Pearson r, Spearman rho, and mean scores.

## Alignment

Transcripts are matched across providers by composite key:
`student_persona | course | exercise_number | transcript_name`.
Missing rows in either provider appear as gaps (NaN) in the line chart.
