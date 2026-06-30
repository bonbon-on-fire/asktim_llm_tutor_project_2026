# Tutor Correctness Eval — Design

**Date:** 2026-06-30
**Status:** Approved design, pending implementation plan
**Author:** brainstormed with Claude

## Problem

The existing Claude-judge (`rubric_08`) grades *pedagogy, dialogue, and
communication* — how the tutor teaches. It does **not** measure whether the
tutor's statements are factually/quantitatively correct. The 324 with-lecture
transcripts scored 37.14/40 vs the 108 baseline's 37.12/40 — no movement,
because the rubric is at a ~93% ceiling and is blind to correctness.

But the reason lectures were added (06/30 meeting notes) is that *some problems
require information from the lecture, and without it the tutor gives wrong
guidance*. We need an eval that measures **tutor correctness** and tests
whether lecture context reduces tutor errors.

## Key constraint: the tutor withholds final answers

AskTIM tutors are designed **not to leak answers** (serious graded course). So
"did the tutor's final answer match the key?" is mostly inapplicable — a
well-behaved tutor never states the final number. Therefore the metric is the
**wrong-claim rate**: of the quantitative/methodological claims the tutor *does*
make (e.g. "single-source from Supplier 3", "your supply constraint should be
≤ capacity", "that subtotal is 91,250"), what fraction are incorrect?

## Goal

Produce a per-transcript wrong-claim rate and compare **baseline (no-lecture)**
vs **lecture arm** to quantify the lecture effect on tutor correctness.

## Global Constraints

- Course under test: `supply_chain_design` (SC2x). 6 problems: exercises
  `01/02/03`, practices `01/02/03`.
- No official answer key exists in the repo; ground truth is built here.
- Judge provider: Claude (Anthropic), matching the existing grading.
- Parallel judging via `ThreadPoolExecutor`, 6 workers (matches
  `internal_ui/run_ui_judge.py:PARALLEL_WORKERS`).
- The wrong-rate denominator counts only `correct + incorrect` claims;
  `unverifiable` and low-confidence facts are excluded and reported.
- Repo convention: git commits omit the `Co-Authored-By: Claude` trailer.

## Architecture

Three isolated components under a new `eval/correctness/` package, plus key
files. Data flows one direction:

```
solver scripts ──build once──> keys/<problem>.json
                                      │
   transcript ──┐                     ▼
                ├──> judge(problem, key, transcript) ──> claim JSON ──> aggregate ──> report + chart
   answer key ──┘        (6 parallel workers)            *_correctness[_lecture]/
```

### Component 1 — Verified answer keys (`eval/correctness/keys/`, `eval/correctness/solve/`)

For each of the 6 problems, a JSON key:

```jsonc
{
  "problem": "exercise_01",
  "facts": [
    { "id": "ga1_part2_total_cost",
      "question": "GA1 Part 2: total weekly cost for Locky Locke (purchase+transport)",
      "answer": 91250, "type": "numeric", "tol_pct": 1.0, "units": "USD/week",
      "method": "scipy.optimize.linprog transportation LP", "confidence": "high" },
    { "id": "ga1_part3_factory2_supplier",
      "question": "GA1 Part 3: which supplier should Factory 2 use under the holistic optimum?",
      "answer": "Supplier 3", "type": "choice", "confidence": "high" }
    // ...
  ]
}
```

- `type ∈ {numeric, choice, multichoice, text}`. Numeric facts carry
  `tol_pct` (relative tolerance) and `units`. Choice/multichoice carry the
  correct option(s).
- Each fact records `method` (how it was derived) and `confidence ∈
  {high, low}`.
- **How built:** solver scripts in `eval/correctness/solve/` compute each fact
  with real code — `scipy.optimize.linprog` / `PuLP` for transportation and
  facility-location LP/MILP; Weiszfeld iteration for Weber (geometric-median)
  parts. Each solver script is the single source for its problem's `high`-
  confidence numeric facts and writes the key file.
- **Low-confidence handling:** any sub-part not solvable by code (conceptual
  "select all correct" MC, qualitative text) is recorded with
  `confidence: "low"` and **excluded** from the wrong-rate denominator. The
  aggregator lists every excluded fact so the team can hand-verify later.
- **Coverage report:** building the keys emits a one-page summary of which
  sub-parts are `high` vs `low` confidence per problem.

### Component 2 — Claim-correctness judge (`eval/correctness/judge.py`, `eval/correctness/prompts/correctness_01.txt`)

Per transcript, one Anthropic call receives the problem text, the answer key
(facts list), and the full ordered tutor turns. It returns structured JSON
(enforced via a tool/JSON schema):

```jsonc
{
  "claims": [
    { "quote": "so your total there is about 88,000",
      "maps_to": "ga1_part2_total_cost",
      "tutor_value": "88000",
      "verdict": "incorrect",
      "reason": "key value is 91,250 (>1% off)" }
  ],
  "n_claims": 7,
  "n_correct": 4,
  "n_incorrect": 1,
  "n_unverifiable": 2,
  "leaked_final_answer": false
}
```

- `verdict ∈ {correct, incorrect, unverifiable}`. `unverifiable` = claim maps
  to no `high`-confidence fact, or is not checkable.
- `leaked_final_answer`: bonus boolean tying to the no-leak concern (did the
  tutor state a graded final answer outright?).
- Output written to `transcripts/<type>/<type>_correctness/` (baseline) and
  `transcripts/<type>/<type>_correctness_lecture/` (lecture arm), one JSON per
  transcript, alongside the source payload.
- Runner mirrors `internal_ui/run_ui_raw.py` / `run_ui_judge.py`:
  `ThreadPoolExecutor(6)`, resume-safe (skip transcripts already judged),
  `--arm {baseline,lecture}` and `--yes` flags, progress logging.

### Component 3 — Aggregate + compare (`eval/correctness/aggregate.py`)

Reads both `*_correctness/` and `*_correctness_lecture/` sets and computes
**wrong-claim rate = Σ n_incorrect / Σ (n_correct + n_incorrect)**:

- overall, per-problem, and per-persona-group, for each arm
- the baseline→lecture delta
- mean `leaked_final_answer` rate per arm
- total verifiable vs unverifiable claim counts (so coverage is visible)

Emits a Markdown comparison table to stdout and a grouped bar chart
(baseline vs lecture wrong-rate per problem) saved under the dashboard's
existing visualization output directory.

### Matched subset

- **Baseline:** all 108 `*_claude` source transcripts (18 personas × 6
  problems × 1 trial).
- **Lecture:** the matched 108 — `trial == 1` for each (persona, problem) —
  selected from the 324 `*_lecture` transcripts, so the arms compare like for
  like.

## Error handling

- Judge API failure on a transcript: logged as `FAILED`, counted, does not
  abort the run; resume re-attempts only missing outputs.
- A transcript with zero tutor claims → `n_claims: 0`, contributes 0/0
  (excluded from rate denominators, counted in a "no-claim transcripts" tally).
- Solver that cannot converge / model infeasible → that fact is dropped to
  `confidence: "low"` with the failure noted, never silently set to a guess.

## Testing

- **Solvers:** each solver script has a unit test asserting its key facts
  against an independently computed value (or tight sanity bounds where no
  external value exists), e.g. the transportation LP optimum recomputed by a
  second method.
- **Judge:** a fixture mini-transcript containing exactly one deliberately
  wrong number and one correct statement → the judge must return
  `n_incorrect == 1` mapping to the right fact, and `n_correct >= 1`.
- **Aggregator:** a fixture pair of claim JSONs with known counts → asserts the
  computed wrong-rate and delta.

## Out of scope (YAGNI)

- Other courses (only SC2x has the lecture/data set under test).
- Grading the full 324 lecture arm (matched 108 is sufficient for the delta;
  full run is a later option if more power is needed).
- A live/UI surface — this is an offline batch eval.
- Re-running simulations or adding a with-data/no-lecture control arm (separate
  decision the user deferred).
