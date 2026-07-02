# Visualization

Generate Claude transcript grading charts. Each run produces **all 11** configured
outputs (no prompts or modes): the six SC2x persona-type evaluation charts
(`01`–`06`) followed by the score-distribution and per-transcript grade charts
(`07`–`11`).

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

This generates all 11 charts, including the SC2x persona-type evaluation charts
(`01`–`06`). To generate only the SC2x charts (bar/heatmap/boxplot by persona and
problem), run the companion module directly:

```powershell
python -m visualization.sc2x_eval_charts
```

### RAG grades

Both modules take a `--rag` flag to chart the RAG-context round (reads
`*_claude_rag/` instead of `*_claude/`). All RAG charts are written together to
`visualization/outputs/rag/`; the default (non-RAG) charts stay in
`visualization/outputs/`:

```powershell
python -m visualization.run_visualization --rag
python -m visualization.sc2x_eval_charts --rag
```

## Outputs

Written to `visualization/outputs/`:

Files use a zero-padded `##_` prefix and start at `07` so they sit after the
sc2x charts (`01`–`06`), which share this folder:

| File | Description |
| ---- | ----------- |
| `07_score_histogram_all.png` | **Histogram** of Claude total scores across all graded transcripts, with mean line and the "answer-giving penalty zone" (≤ max−12) shaded. Annotates n, mean, median, % perfect, and % in the penalty zone. |
| `08_grades_all_transcripts.png` | Line chart of Claude **total score** per transcript, all personas combined. |
| `09_grades_chaotic_transcripts.png` | Same chart restricted to chaotic persona. |
| `10_grades_clueless_transcripts.png` | Same chart restricted to clueless persona. |
| `11_grades_cooperative_transcripts.png` | Same chart restricted to cooperative persona. |

The SC2x charts (`sc2x_eval_charts`, `01`–`06`) are written to the same
`visualization/outputs/` folder (or `visualization/outputs/rag/` with `--rag`).

Annotation box shows transcript count and mean score. Y-axis uses integer ticks.

## Sorting

Rows are ordered with the same key as other tooling: persona type, full student persona, course, exercise number, then transcript number.
