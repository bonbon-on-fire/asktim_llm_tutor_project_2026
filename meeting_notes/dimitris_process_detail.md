# AskTIM — Detailed Project Workflow, Decisions & Results

Companion to [dimitris_meeting_deck.md](dimitris_meeting_deck.md). This is the long-form,
evidence-backed version: the exact steps we took, *why*, and the results/numbers at each stage.
Written to be readable by someone seeing the project for the first time — every rubric term and
number is explained where it appears. Sources: the weekly meeting notes (`meeting_notes/`), the
committed score data (`judge/claude_transcript_scores.tsv`), the grading rubric
(`judge/rubrics/rubric_08.md`), the hand-grade workbook, and git history.

---

## The one-paragraph version

AskTIM is a **Socratic tutor** for MIT OpenCourseWare assignments — it guides students with
questions and **never hands over the answer**. The hard part isn't building a chatbot; it's
*proving* the chatbot stays in that role with real students. So most of the project is a
**test-and-measure loop**: we build/modify the tutor, have **simulated "student" bots** hold
conversations with it, have a separate **"judge" AI grade each conversation** against a fixed
checklist (the *rubric*), read the scores, change one thing, and repeat. Once the scores said the
tutor was reliable, we **deployed it live** in a real course and started watching real usage.

```
build/modify tutor → simulate conversations → judge grades them → read results → change one thing → repeat
```

---

## What the judge actually checks (the rubric, in plain English)

The judge reads a whole conversation and **starts every category at full marks, then subtracts
points for specific mistakes**. Today's rubric (`rubric_08`) is worth **40 points**, split into
seven checks:

| Check (rubric code) | In plain English | Max pts |
|---|---|---|
| **1.1 Socratic / no direct work** | Did the tutor avoid doing the student's work? Lose **all 12** if it produces near-submission-ready answers. **This is the core guarantee.** | 12 |
| **1.2 Scaffolding** | Did it build on what the student got right, and figure out *what* they're confused about before answering? | 6 |
| **1.3 Meta-learning** | Did it coach the student's *method* (how to reason), not just whether they're right? | 2 |
| **2.1 No spiraling** | Did it avoid looping on the same question without progress? | 4 |
| **2.2 Stay on the assignment** | Did it keep the student on the actual task and redirect off-topic chat? | 8 |
| **3.1 Bite-sized & clear** | Short, focused replies instead of walls of text? | 4 |
| **3.2 Supportive tone** | Encouraging coach, not a cold grader (no letter grades)? | 4 |
| | **Total** | **40** |

When this doc says e.g. *"section 1.1"* it means that first row — the never-do-the-student's-work
rule. That's the one that matters most.

---

## Phase 1 — Build the test harness (Feb 24 – Mar 10, 2026)

**What we did**
- Stood up the core loop: **student bots → conversations → a judge that scores them.** (02/24)
- Fixed a model bug — the tutor and students were quietly running on an older model (GPT-4o); switched everything to the current model. (02/24)
- Gave the **student bots the actual assignment text** — at first only the tutor had it, so the simulated students couldn't engage realistically. (02/24)
- Reframed the "chaotic / clueless" bots from *characters* into **stress-testers**: each one tries to trigger one specific tutor failure (demanding the answer, playing dumb, going off-topic). Added rules so they mix tactics and don't repeat themselves. (03/03)
- **Automated the matrix**: every student type × every exercise × N repeats, with the course description fed in as context. Saved every conversation plus the judge's scores to disk. (03/03)
- Split the judge's **instructions** from its **rubric checklist** into separate versioned files and made the judge's scores **whole numbers only** (no fractional points). (03/10)

**Why** — Reading conversations by hand doesn't scale and isn't repeatable. We needed a push-button
harness so any change to the tutor could be re-tested the exact same way. And we used *adversarial*
testers, not "average students," because the failure we most needed to catch before launch is the
tutor **caving and giving the answer under pressure**.

**Results** — Settled the cadence: ~10-turn conversations, multiple student types, several
exercises. First rubric cleanup removed redundant checks and set the headline rule: **lose all of
the pedagogy points if the tutor gives the answer.**

---

## Phase 2 — Make the judge trustworthy (Mar 17 – Apr 7, 2026)

Before trusting any tutor score, we had to trust the judge. The test: **have two different AI
judges (GPT and Claude) grade the same conversations and see if they agree.** If two competent
judges disagree, the rubric is the problem, not the tutor.

**What we did**
- Made the rubric **deductions-only** (removed bonus points) and more detailed. (03/17)
- Ran **GPT and Claude as judges side by side** and measured their disagreement on each conversation. (03/17)
- When they disagreed too much, **trimmed over-specified rubric language and removed "malus" (extra whole-section penalties)**. (03/20)
- Built **self-consistency checks** — grade the *same* conversation twice with the *same* judge and see if the score is stable — and per-category heat maps to find where the disagreement lived. (03/31)
- Simplified the worst category, **3.1 (response length/clarity)**, which was causing the most disagreement. (03/31)
- Compared rubric versions and adopted **`rubric_08`**, which drops one hard-to-judge sub-check (reflection after a student recovers from a mistake) — the tutor still *does* it, we just stopped *scoring* it. (04/07)

**Why** — Inter-judge agreement is a cheap, objective proxy for "is this rubric well-defined?"

**Results / numbers**
- The disagreement was worst in the **response-length category (3.1)** and traced to rubric wording being too strict (Claude followed it literally, GPT loosely). (03/20)
- Self-consistency verdict: **Claude was far more stable than GPT.** Claude graded the same conversation about the same way each time (self-consistency ≈ **0.8**); GPT was too erratic to be the official grader. The biggest remaining wobble was in **section 1.1**, where Claude's penalty swung between **6 and 12 points**. (04/07)
- **Decision: Claude becomes the official judge; GPT judging dropped.** The rubric total settled from **46 points down to 40** as we simplified it. (04/07)

---

## Phase 3 — Improve the tutor, one prompt at a time (Apr 13 – May 1, 2026)

With a trustworthy judge, we focused on the tutor's wording.

**What we did**
- **Spot-checked the judge against ourselves**: three of us hand-graded the same 20 conversations with the same rubric and compared to Claude's scores. (04/13)
- Switched to **fast, small runs** (~10 conversations with one targeted student type) so each tutor tweak could be tested quickly. (04/13)
- Built a **"fork-at-the-broken-turn" tool**: instead of regenerating a whole conversation to test a fix, we replay an existing one up to the exact turn where the tutor slipped, then let the *new* tutor wording take over from there. That isolates the change. (04/16–04/22)
- Ran a head-to-head: **30 conversations, the old tutor wording vs the new one**, graded both. (04/22–04/28)
- Added each course's **syllabus** to the tutor's context. (05/01)

**Why** — Regenerating a whole conversation makes every tweak look like a brand-new chat, so you
can't tell if *your edit* caused a score change. Forking at the broken turn gives a clean A/B test.

**Results / numbers**
- **Human spot-check (the honest version):** Claude showed **moderate agreement** with the two of us who actually varied our scores — rank-correlation (Spearman) **0.59 with Nishita** and **0.57 with Romain** — and Claude's average (**31.8 / 40**) matched the stricter human grader almost exactly (Nishita averaged 31.9). Read: **Claude grades consistently and on the strict side** — good enough to *rank* tutor versions against each other, though not a perfect stand-in for a human. *(Caveat: only 20 conversations; a third grader's sheet was left unfilled, so don't over-read a single pooled number.)*
- **The tutor win:** the new wording (**`tutor_05`**) **lost zero points for giving away the answer** across the 30-conversation comparison — the previous version had been caught handing over fill-in-the-blank skeletons. This is the headline improvement: the never-give-the-answer guarantee held.
- **A finding that changed strategy:** the chaotic/clueless bots had started behaving unrealistically (getting "lost" on trivially simple terms), so they'd stopped surfacing *new* bugs. We concluded the next real bugs would come from **human testing**, not more bot runs. (04/28)
- **A context finding:** without the syllabus, the tutor would **hallucinate what the class had covered**. Adding course context fixed it. (05/01)

---

## Phase 4 — Deploy AskTIM live (May 5 – Jun 4, 2026)

**What we did** — Built the real student web app: it logs conversations to a database, **embeds
inside the MIT Learn assignment page** (via an iframe), gives each student a lightweight
**email + password identity** (a popup after their 3rd message, so history follows them across
browsers), **streams** the tutor's reply as it types, and shows a history sidebar. Hosted it on
**Railway** (a cloud host) for the semester, with a plan to move the data in-house after the course
ends. Also built a **Sandbox** version for TAs/devs to try any course or prompt without touching
the live database.

**Why** — MIT Learn embeds tools via iframe on the assignment page, so an embeddable,
identity-aware, persistent web app was the deployable shape; Railway was the fastest path to a
managed database + deploys for one semester.

**Results / numbers** — "Cities and Climate Change" launched with **~120 students** (8 for credit);
realistic expectation was **~20 students** using the tutor. 13-week semester; live by Week 2.

---

## Phase 5 — Early real usage & cross-course expansion (Jun 9 – present)

**Real usage so far (first week live; logs on Railway, 06/09):**
- **4 unique conversations**, and **all four were logistics** — students asking *how to submit the table* for the "Power/Actor Map" assignment, not about the content.
- The tutor **handled them appropriately.** Read: the early exercises are simple enough that students don't yet need conceptual help.
- Reach: **~15 verified + ~100 audit learners; ~20–25 active.**

**Cross-course stress test (this week):** to show the tutor generalizes beyond climate/urban
studies, we ran the same simulate-and-judge pipeline on four new courses (two STEM, two
humanities):
- **414 conversations** generated (18 student types × 23 exercises) and **all 414 graded by the Claude judge**, mean **38.2 / 40**, **zero grading failures**.
  - By student type: **cooperative 39.8, chaotic 38.0, clueless 36.8** — exactly the expected order (easiest to hardest to tutor).
  - By course: **math 38.3, physics 38.3, meaning-of-life 37.5** — tightly clustered, i.e. the tutor behaves consistently across very different subjects.
- A fourth course (International Development Planning, **432 more conversations**) is generating now.

---

## Specific results, backed by committed data

**The big historical scoreboard** (`judge/claude_transcript_scores.tsv` — every simulated
conversation we generated and graded with the current rubric, out of 40):

- **889 conversations graded.** Mean **36.8 / 40**, median **38**.
- **49% scored a perfect 40**, and only **15 (~1.7%)** dropped to 28 or below (the band where the tutor lost the big "did the student's work" penalty). So **the never-give-the-answer failure is rare.**
- By student type: **cooperative 39.5**, **chaotic 36.3**, **clueless 35.2** — the tutor does best with cooperative students and is most challenged by genuinely lost ones (consistent with the new-course run above).

**Visualization artifacts** (`visualization/outputs/`, screenshot-ready for slides): per-student-type
score charts, the **old-tutor-vs-new-tutor** comparison bars (the `tutor_05` win), and the
**human-vs-Claude** scatter charts with the correlation annotated.

---

## Consolidated numbers (with source)

| Metric | Value | Source |
|---|---|---|
| Judges compared | GPT vs Claude → **Claude chosen** (more self-consistent, ≈0.8) | 04/07 |
| Rubric total | **46 → 40 points** as it was simplified | 03/20 → 04/07 |
| Human spot-check agreement | **moderate**: Spearman **0.59** (Nishita), **0.57** (Romain); Claude avg 31.8 ≈ strict grader | recomputed from workbook + TSV |
| Tutor improvement | new wording (`tutor_05`) lost **0 points for giving away answers** (30-convo test) | 04/28 |
| Historical scoreboard | **889** graded, mean **36.8/40**, **49% perfect**, ~1.7% with the big penalty | `claude_transcript_scores.tsv` |
| New-course test (this week) | **414** graded, mean **38.2/40**, 0 failures | this week |
| In progress | **432** more (Intl Development Planning) | this week |
| Live course | ~**120** students (8 for credit), ~20 expected users | 05/19 |
| First real usage | **4** conversations, all logistical; ~20–25 active | 06/09 |

---

### Caveats to verify before presenting
- The human-vs-Claude correlation is from a **small sample (20 conversations)** and one grader's
  sheet was unfilled — present it as "moderate agreement on a spot-check," not a definitive
  validation.
- Course code appears as both **"11.024x"** (early docs) and **"11.270x"** (deployment) — confirm
  the right one.
- `meeting_notes/05_08_2026.md` still contains an unresolved git merge-conflict marker (and
  `05_12_2026.md` duplicates it) — worth cleaning up.
