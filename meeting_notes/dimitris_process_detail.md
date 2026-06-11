# AskTIM — Detailed Project Workflow, Decisions & Results

Companion to [dimitris_meeting_deck.md](dimitris_meeting_deck.md). This is the long-form,
evidence-backed version: the exact steps we took, *why* we took them, and the results/stats at
each stage. Sourced primarily from the weekly meeting notes (`meeting_notes/MM_DD_2026.md`) and
the repo artifacts (rubrics, judge, transcripts, visualization outputs).

**The whole project is one loop, run repeatedly:**
> build/modify the tutor → simulate conversations with student bots → grade them with an LLM judge against a rubric → read the results → change one thing → repeat. Once the tutor was trusted, we deployed it and started watching real usage.

---

## Phase 1 — Build the evaluation harness (Feb 24 – Mar 10, 2026)

**What we did**
- Stood up the core pipeline: **student personas → generated multi-turn conversations → LLM judge scores them** against a rubric. (02/24)
- Fixed a model bug: tutor and students were silently running on **GPT-4o / GPT-4o-mini**; switched everything to **GPT-5.2**. (02/24)
- Gave the **student bots the assignment text** — originally only the tutor had it, so simulated students couldn't engage realistically. (02/24)
- Reframed "chaotic" and friends from *student characters* into **adversarial tester / jailbreak personas**, each probing one tutor failure mode; added rules to mix tactics, avoid cyclic repetition, and make real exercise progress when that helps surface bad tutor behavior. (03/03)
- Automated the matrix: **each persona × each exercise × N trials**, with course-description context injected. Built a consolidated results artifact (deductions + explanations) and a CSV (scores + transcript + deductions). (03/03)
- Split the judge **prompt** out from the **rubric** into separate versioned files; moved to `tutor_02`; made judge scoring **integer-only** with net totals computed in code (not by the model). (03/10)

**Why**
- Reading conversations by hand doesn't scale and isn't reproducible — we needed an automated, versioned harness so any tutor change could be re-tested identically.
- Adversarial personas, not "realistic students," because the risk we most needed to catch before launch was the tutor **giving away answers under pressure**.

**Results / data**
- Target generation cadence: **2 conversations per persona, ~10 turns each, across 4 exercises**. (02/24)
- First rubric surgery: dropped redundant sections 2 & 4; **1.1 = full 5-point deduction** if the tutor gives the answer; merged **2.2+2.3 → 5 pts**, **2.1 → 3 pts**. (03/03–03/10)
- Working-model target set for **end of March**, with a 4-week buffer. (03/03)

---

## Phase 2 — Judge calibration & cross-model agreement (Mar 17 – Apr 7, 2026)

This phase was about earning trust in the **judge** before trusting any tutor score.

**What we did**
- Made the rubric **hierarchical** (`#.#.#`) and switched to **deductions-only** (removed bonus points) — strict grading preferred over lenient. (03/17)
- Ran **both Claude and GPT as judges** on every transcript and measured how much they disagreed per transcript. (03/17)
- When agreement dropped, **trimmed over-specified criteria and removed section "malus" deductions**, landing on a **46-point total** (this is `rubric_05`). (03/20)
- Tried **bundle judging** — grading transcripts in **bundles of 3 and 6** with different persona compositions — to test whether judging context reduced variance. (03/20)
- Built **self-consistency** analysis (GPT-vs-GPT, Claude-vs-Claude) and per-section/per-persona **heatmaps** to localize disagreement. (03/31)
- Simplified the worst-offending criterion (**section 3.1 → 4 pts max**, merged sub-items, removed subjective ones). (03/31)
- Compared **rubric_07 vs rubric_08** and adopted **rubric_08**, which drops subsection **1.3.C** ("fails to prompt reflection after success following failure") — kept as tutor *behavior* but no longer *scored*. (04/07)

**Why**
- If two strong judges disagree on the same transcript, the rubric — not the tutor — is the problem. We optimized for **inter-judge agreement** as a proxy for rubric quality.

**Results / data**
- **GPT–Claude correlation dropped significantly** in one run → root-caused to rubric over-specificity (Claude follows wording strictly; GPT is more lenient). (03/20)
- Disagreement was **concentrated in section 3.1**; coupling flags found (e.g. 1.2 ↔ 3.2). (03/31)
- Self-consistency verdict: **Claude was substantially more stable than GPT** (Claude self-correlation ≈ **0.8**); GPT's self-consistency was too low to be a primary judge. Biggest remaining instability was **section 1.1**, where deductions swung between **6 and 12 points**. (04/07)
- **Decision: Claude becomes the primary judge; GPT judging paused; bundle/batch framework dropped.** (04/07)
- Rubric total moved **46 → 40 points** (rubric_05 → rubric_08).

---

## Phase 3 — Tutor prompt iteration via "mini" re-runs (Apr 13 – May 1, 2026)

With a trusted judge, we turned to improving the **tutor**.

**What we did**
- Validated Claude-as-grader against humans: built an **Excel hand-grade workbook** and compared human scores to Claude's. (03/31–04/13)
- Switched to **short-burst generation** (~10 transcripts with one targeted persona) for fast iteration instead of giant batches. (04/13)
- Built **`run_ui_raw_mini`**: instead of regenerating a whole conversation to test a prompt tweak, **fork an existing transcript at the faulty turn** and only re-run from there — so you isolate the exact behavior you're fixing. Audited it so a turn's hidden `pedagogical_reasoning` doesn't leak into later turns. (04/16–04/22)
- Curated a **reference table of specific failure turns** (e.g. `chaotic 0007 turn 3 → 1.1.C`, `clueless 0013 turn 1 → 1.2.B`, `clueless 0123 turn 8 → positive benchmark`) to iterate against. (04/16)
- Ran **30 transcripts (10 per prompt × 3 prompt variants)**, graded originals (tutor_04) vs minis (tutor_05), and plotted the comparison. (04/22–04/28)
- Added **syllabus files** to course context and wired them into the system prompt. (05/01)

**Why**
- Full regeneration makes every tweak look like a brand-new conversation, so you can't attribute a score change to your edit. Re-running only the **pivot turn** gives a clean A/B.
- Hand-grade correlation was the human check on the automated judge before we relied on it for prompt selection.

**Results / data**
- **Hand-grade vs Claude correlation was high** (the visualization annotates exact Pearson/Spearman per grader: `hand_grades_{faizan,romain,nishita}_vs_claude.png`) — enough to trust Claude-led grading. (04/13)
- **`tutor_05` was the clear winner: the judge removed *zero* points for giving away the answer (spoon-feeding)** across the 30-transcript comparison — the headline improvement. (04/28)
- Concrete before/after: chaotic transcript 7, turn 3 — `tutor_04` handed over a fill-in skeleton; **`tutor_05` refuses to ghostwrite**. (04/28)
- Key realization: chaotic/clueless personas had **served their purpose** and were becoming unrealistic ("lost over very simple terms"); the next source of real bugs is **human testing**, not more AI-student runs. (04/28)
- Hallucination finding: without course context the tutor **invents what the student has been taught** → motivated adding syllabus now and lecture notes later. (05/01)

---

## Phase 4 — Deployment: AskTIM goes live (May 5 – Jun 4, 2026)

**What we did**
- Built **`main_ui`** — the production student app: Postgres conversation logging, **iframe embed** for MIT Learn, **email+password soft identity** (popup after the 3rd message, cookie carries across browsers), **token streaming** ("AskTIM is thinking…" → types out), history sidebar, permanent course branding + beta label. (05/08–05/19)
- Hosted on **Railway** (managed Postgres, container deploy) with a plan to **wipe Railway and migrate data internally** after the course ends. (05/19)
- Added AskTIM **self-context** files so the tutor knows what it is, and pointed `about_asktim.txt` at the `tutor_*` prompt for the actual rules (instead of duplicating them). (05/19–05/22)
- Built the **Sandbox (`test_ui`)** — same chat plus an Edit-context switcher and a Create-context wizard, on its own Postgres DB — so TAs/devs can trial any course/exercise/prompt without touching production. (06/01)

**Why**
- MIT Learn embeds tools via iframe on the assignment page, so an embeddable, identity-aware, persistent web app was the deployable shape. Railway gave the fastest path to managed Postgres + deploys for a single semester.

**Results / data**
- "Cities and Climate Change" launched with **~100 → 120 students** (8 taking it for credit); realistic estimate **~20 active tutor users**. (05/08–05/19)
- **13-week** semester; deploy by **Week 2**; image context targeted for **Week 4 / exercise 4**. (05/08–05/22)

---

## Phase 5 — Early real usage & cross-course expansion (Jun 9 – present)

**What we did / found**
- Reviewed the **first real usage** in 11.270x and planned the Dimitris materials. (06/09)
- Expanded testing to **new STEM + humanities courses** using the same simulate-and-judge pipeline (this week's work): Mathematics for Computer Science, Physics III, The Meaning of Life, Intro to International Development Planning.

**Results / data — first week of real usage (06/09, logs on Railway)**
- **4 unique AskTIM conversations**, **all logistical** (how to submit the table for the **Assignment 4 "Power/Actor Map"**), none about substance.
- Tutor **responded appropriately**; read as exercises being too elementary to need conceptual help yet.
- Reach: **~15 verified + ~100 audit learners; ~20–25 active**; announced via pinned announcement + email.

**Results / data — cross-course simulation (this week)**
- Generated **414 transcripts** across 3 new courses (Math, Meaning of Life, Physics) — 18 personas × 23 exercises — and graded all 414 with the **Claude judge (judge_08 / rubric_08)**.
- **Mean score 38.2 / 40** (min 25, max 40), **0 grading failures**.
  - By persona: **cooperative 39.8**, **chaotic 38.0**, **clueless 36.8** (reads correctly — cooperative students are easiest to tutor well, lost students hardest).
  - By course: **math 38.3**, **physics 38.3**, **meaning-of-life 37.5** (tightly clustered → tutor behaves consistently across subjects).
- A 4th course (Intro to International Development Planning, 24 exercises × 18 personas = **432 transcripts**) is generating now; judging to follow.

---

## The rubric, and how it evolved

The judge scores a **full conversation**, **deductions only** (start at full points, subtract on evidence). Each behavior is penalized in exactly one place to avoid double-counting.

**Evolution:** remove redundant sections 2 & 4 (02/24) → merge 2.2+2.3, integer-only scoring (03/10) → deductions-only, no bonus (03/17) → **remove malus, 46-pt total = rubric_05** (03/20) → simplify 3.1 (03/31) → **drop 1.3.C, 40-pt total = rubric_08** (04/07, current).

**Current rubric (`rubric_08`, 40 pts):**

| Section | Sub-criteria | Max |
|---|---|---|
| 1. Pedagogy | 1.1 Socratic/no-direct-work (12) · 1.2 Scaffolding (6) · 1.3 Meta-learning (2) | **20** |
| 2. Dialogue quality | 2.1 Redundancy (4) · 2.2 Assignment anchoring (8) | **12** |
| 3. Communication quality | 3.1 Bite-sized/clear (4) · 3.2 Tone & formative framing (4) | **8** |
| **Base total** | | **40** |

The single biggest penalty (all 12 points of 1.1) fires if the tutor produces near-submission-ready work — i.e. the core "never give the answer" guarantee.

---

## Consolidated stats (with source date)

| Metric | Value | Source |
|---|---|---|
| Generation cadence (early) | 2 convos/persona, ~10 turns, 4 exercises | 02/24 |
| Model | GPT-4o/4o-mini → **GPT-5.2** | 02/24 |
| Rubric total | **46** (rubric_05) → **40** (rubric_08) | 03/20 → 04/07 |
| Bundle-judging experiment | bundles of **3** and **6** (later dropped) | 03/20 |
| Hand-grade target | **30** → **20** transcripts (10/persona) | 03/31 → 04/07 |
| Claude judge self-consistency | ≈ **0.8** (vs GPT too low) → Claude primary | 04/07 |
| Section 1.1 instability | deductions swing **6 ↔ 12** pts | 04/07 |
| Hand-grade vs Claude | high correlation (Pearson/Spearman on charts) | 04/13 |
| Tutor prompt comparison | **30 transcripts** (10 × 3 prompts), tutor_04 → **tutor_05** | 04/22–04/28 |
| tutor_05 headline result | **0 points deducted for spoon-feeding** | 04/28 |
| Course enrollment | ~100 → **120** (8 for credit), ~**20** expected active | 05/08–05/19 |
| First real usage | **4 conversations**, all logistical; ~20–25 active | 06/09 |
| Cross-course sim (this week) | **414** transcripts graded, **mean 38.2/40**, 0 failures | this week |
| In progress | **432** more transcripts (intl-dev planning) | this week |

**Visualization artifacts** (`visualization/outputs/`): per-persona Claude score charts, tutor_05 score charts, **original-vs-mini** comparison bars (the tutor_04→tutor_05 win), and **hand-grade-vs-Claude** correlation charts with Pearson/Spearman annotations — all screenshot-ready for the deck.

---

### Caveats to verify before presenting
- Course code appears as both **"11.024x"** (early exercise docs) and **"11.270x"** (deployment) — confirm the correct one.
- The **0.8 Claude self-consistency** and "high" hand-vs-Claude correlation are stated **qualitatively** in the notes; pull the exact coefficients off the visualization charts if you want hard numbers on a slide.
- `meeting_notes/05_08_2026.md` contains an unresolved git merge-conflict marker and `05_12_2026.md` duplicates it — worth cleaning up.
