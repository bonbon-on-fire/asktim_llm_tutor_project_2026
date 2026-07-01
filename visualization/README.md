# Visualization

Generate Claude transcript grading charts. Each run produces **all** configured outputs (no prompts or modes).

## Inputs

**Claude machine grades** — judged transcript JSON files:

- `transcripts/<persona_type>/<persona_type>_claude/transcript_*.json` — standard Claude grades

Paths follow the current repo layout: one folder per persona family (`chaotic`, `cooperative`, `clueless`) with graded subfolders.

## Run

Install dependencies from the repo root, then run:

```powershell
pip install -r requirements.txt
python -m visualization.run_visualization
```

For the SC2x persona-type evaluation charts (bar/heatmap/boxplot by persona and
problem), run the companion module:

```powershell
python -m visualization.sc2x_eval_charts
```

## Outputs

Written to `visualization/outputs/`:

| File | Description |
| ---- | ----------- |
| `claude_score_histogram_all.png` | **Histogram** of Claude total scores across all graded transcripts, with mean line and the "answer-giving penalty zone" (≤ max−12) shaded. Annotates n, mean, median, % perfect, and % in the penalty zone. |
| `claude_grades_all_transcripts.png` | Line chart of Claude **total score** per transcript, all personas combined. |
| `claude_grades_chaotic_transcripts.png` | Same chart restricted to chaotic persona. |
| `claude_grades_clueless_transcripts.png` | Same chart restricted to clueless persona. |
| `claude_grades_cooperative_transcripts.png` | Same chart restricted to cooperative persona. |

The SC2x charts (`sc2x_eval_charts`) are written to `visualization/outputs/sc2x/`.

Annotation box shows transcript count and mean score. Y-axis uses integer ticks.

## Sorting

Rows are ordered with the same key as other tooling: persona type, full student persona, course, exercise number, then transcript number.
