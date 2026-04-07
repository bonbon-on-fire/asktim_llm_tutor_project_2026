# Visualization

Generate score comparison charts for GPT vs Claude transcript grading.

## Inputs

Reads judged transcript JSON files from:

- `transcripts/<persona_type>/<persona_type>_gpt/transcript_*.json`
- `transcripts/<persona_type>/<persona_type>_claude/transcript_*.json`
- `transcripts/<persona_type>/<persona_type>_gpt_v2/transcript_*.json`
- `transcripts/<persona_type>/<persona_type>_claude_v2/transcript_*.json`
- `transcripts/<persona_type>/<persona_type>_gpt_v3/transcript_*.json`
- `transcripts/<persona_type>/<persona_type>_claude_v3/transcript_*.json`
- `judge/hand_grade_judge.xlsx` (sheet: `compiled grading`, rows where `grader name = faizan`)

## Run

```powershell
python -m visualization.run_visualization
```

## Outputs

Written to `visualization/outputs/`:

| # | File | Description |
| - | ---- | ----------- |
| 1 | `section_discrepancy_by_rubric_section_gpt_vs_claude.png` | Bar chart of per-section grading discrepancies on paired transcripts (mean absolute difference), with `n` and signed mean delta annotations. |
| 2 | `subsection_discrepancy_by_subsection_gpt_vs_claude.png` | Subsection (`X.X`) discrepancy chart for regular graded transcripts, with `n` and signed mean delta annotations. |
| 3 | `individual_grades_all_transcripts_gpt_vs_claude.png` | Single line chart of total scores per individual transcript across all personas and versions. |
| 4 | `subsection_correlation_heatmap_all_providers_all_personas_normalized.png` | Joined subsection-pair Pearson correlation heatmap on normalized subsection scores (`score / max`) across GPT + Claude combined; title and axis labels include `n` counts. |
| 5 | `subsection_correlation_heatmap_gpt_all_personas_normalized.png` | Subsection-pair Pearson correlation heatmap on normalized subsection scores (`score / max`) for GPT across all personas; title and axis labels include `n` counts. |
| 6 | `subsection_correlation_heatmap_claude_all_personas_normalized.png` | Subsection-pair Pearson correlation heatmap on normalized subsection scores (`score / max`) for Claude across all personas; title and axis labels include `n` counts. |
| 7 | `hand_grades_faizan_vs_gpt_vs_claude.png` | Exact-transcript comparison chart for Faizan hand grades vs GPT and Claude, with Pearson/Spearman correlations. |
| 8 | `hand_grades_faizan_vs_claude_subsection_heatmap_xxx.png` | Heatmap of subsection (`X.X.X`) deduction correlation between Faizan hand grading and regular Claude grading on exact transcript matches. |
| 9 | `section_discrepancy_by_rubric_section_gpt_vs_claude_v2.png` | Same as #1, but computed only from `_v2` graded transcripts. |
| 10 | `subsection_discrepancy_by_subsection_gpt_vs_claude_v2.png` | Same as #2, but computed only from `_v2` graded transcripts. |
| 11 | `individual_grades_all_transcripts_gpt_vs_claude_v2.png` | Same as #3, but computed only from `_v2` graded transcripts. |
| 12 | `subsection_correlation_heatmap_all_providers_all_personas_normalized_v2.png` | Same as #4, but computed only from `_v2` graded transcripts. |
| 13 | `subsection_correlation_heatmap_gpt_all_personas_normalized_v2.png` | Same as #5, but computed only from `_v2` graded transcripts. |
| 14 | `subsection_correlation_heatmap_claude_all_personas_normalized_v2.png` | Same as #6, but computed only from `_v2` graded transcripts. |
| 15 | `section_discrepancy_by_rubric_section_gpt_vs_claude_v3.png` | Same as #1, but computed only from `_v3` graded transcripts. |
| 16 | `subsection_discrepancy_by_subsection_gpt_vs_claude_v3.png` | Same as #2, but computed only from `_v3` graded transcripts. |
| 17 | `individual_grades_all_transcripts_gpt_vs_claude_v3.png` | Same as #3, but computed only from `_v3` graded transcripts. |
| 18 | `subsection_correlation_heatmap_all_providers_all_personas_normalized_v3.png` | Same as #4, but computed only from `_v3` graded transcripts. |
| 19 | `subsection_correlation_heatmap_gpt_all_personas_normalized_v3.png` | Same as #5, but computed only from `_v3` graded transcripts. |
| 20 | `subsection_correlation_heatmap_claude_all_personas_normalized_v3.png` | Same as #6, but computed only from `_v3` graded transcripts. |
| 21 | `individual_grades_gpt_regular_vs_v3.png` | Per-transcript line chart comparing regular GPT grades versus `_v3` GPT grades. |
| 22 | `individual_grades_claude_regular_vs_v3.png` | Per-transcript line chart comparing regular Claude grades versus `_v3` Claude grades. |

All charts include Pearson r, Spearman rho, and mean scores.

## Alignment

Individual transcripts are matched across providers by composite key:
`student_persona | course | exercise_number | transcript_name`.

Missing rows in either provider appear as gaps (NaN) in the line charts.
