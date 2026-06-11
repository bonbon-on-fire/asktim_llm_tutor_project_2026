---
marp: true
title: AskTIM — Project Review for Dimitris
paginate: true
---

<!--
Slide deck for the Dimitris meeting (rescheduled to June 2026 due to Faizan's conflict).
Content sourced primarily from meeting_notes/ — especially 06_09_2026.md and 03_20_2026.md.
Render with Marp (VS Code "Marp for VS Code" extension → Export) or read as plain notes.
Speaker notes are in HTML comments under each slide.
-->

# AskTIM
### A Socratic LLM Tutor for MIT OpenCourseWare

Project review — June 2026

**Team:** Nishita Bhakar · Romain Puech · Faizan Siddiqi

<!--
Framing: AskTIM is live for 11.270x; this deck walks Dimitris through what we built,
why, what early deployment showed, and where we go next.
-->

---

## What AskTIM is

- A **Socratic tutor** for MIT OCW humanities / social-science assignments — it **never gives the answer directly**, using guided discovery and bite-sized, formative responses.
- **Deployed live** as an iframe-embeddable chat app for **MIT 11.270x — Cities and Climate Change (Spring 2026)**.
- Backed by a full **validation framework**: simulated student bots, an LLM judge that grades conversations against a rubric, and a dashboard to review results before anything reaches real learners.

<!--
Two goals: (1) deployment — a reliable Socratic tutor for OCW; (2) validation — a reproducible
eval framework to test/grade tutor behavior before deployment.
-->

---

## Timeline (Feb → June 2026)

| When | Milestone |
|------|-----------|
| **Feb 2026** | Project kickoff; first working tutor + first adversarial "chaotic" student; grading rubric drafted; judge implemented; terminal runner |
| **Mar 2026** | Reworked into clean pipeline (curriculum / tutor / judge / transcripts); rewrote persona prompts; added course context + turn-size as inputs; batch generation |
| **Mar 20** | Judge/rubric review: GPT–Claude score correlation dropped → simplified rubric, removed malus deductions, expanded dataset |
| **Apr 2026** | Hand-grade calibration workbook; GPT vs Claude visualizations; bundle judging; **tutor_05**; mini-continuation re-runs |
| **May 2026** | Token streaming ("AskTIM is thinking…" → types out); web_ui → **AskTIM Sandbox (test_ui)**; AskTIM context added to tutor + syllabus |
| **Jun 1–4** | **Railway deployment** of student app (main_ui); Sandbox rebrand + Create-context wizard; Postgres for Sandbox |
| **Spring 2026** | **AskTIM goes live in 11.270x**, announced via pinned announcement + email |
| **Jun 9** | Review of first real 11.270x usage; plan Dimitris meeting; expand testing to new courses |
| **This week** | Added 4 test courses (math, meaning-of-life, physics, intl-dev planning); ran persona simulations + judge |
| **Jun 2026** | **Dimitris meeting** (rescheduled — Faizan conflict) |

<!--
Source: git history + meeting_notes/. Emphasize the arc: build tutor → build evaluation →
iterate on prompt/rubric → deploy → observe real usage → expand testing.
-->

---

## Project workflow — what we did, in order

1. **Built the tutor** — LangGraph agent, Socratic system prompt, hidden "pedagogical reasoning" field so the model reasons before replying.
2. **Built adversarial student bots** — personas that each probe one failure mode (demanding answers, going off-topic, lecturing a lost student).
3. **Built an LLM judge + rubric** — grades each finished conversation against a structured rubric (JSON, auto-repair on bad output).
4. **Iterated the tutor prompt** — used judge scores to compare versions (→ tutor_05) and tighten Socratic behavior.
5. **Built review tooling** — dashboard to browse conversations + grades; charts comparing GPT vs Claude judges.
6. **Deployed AskTIM** — student app on Railway for 11.270x; a Sandbox app for TAs/devs to test custom contexts.
7. **Expanded testing** — ran the same simulation + judge pipeline across new STEM and humanities courses.

<!--
"First we did X, then Y": this is the process narrative. Each step exists because the previous
one exposed a need (e.g., we built the judge because eyeballing transcripts didn't scale).
-->

---

## Why these choices (rationale)

- **Never-answer Socratic design** → the pedagogical goal is *learning*, not task completion; an answer-giving bot would undermine the assignment.
- **Hidden pedagogical-reasoning field** → makes GPT "think out loud" privately before replying, which consistently improves its restraint (it stops blurting answers).
- **Adversarial student personas** → real OCW students range from cooperative to answer-hunting to lost; we needed to stress-test all three *before* launch, cheaply and repeatably.
- **Separate LLM judge + explicit rubric** → objective, reproducible scoring across prompt versions; eyeballing transcripts doesn't scale or stay consistent.
- **Simplified rubric, removed malus (Mar 20)** → over-strict rubric wording inflated GPT–Claude disagreement; trimming it improved inter-judge agreement.
- **Iframe-embeddable web app on Railway** → MIT Learn embeds the tutor on the assignment page via iframe; Railway gives us managed Postgres + simple deploys.
- **Separate Sandbox app** → lets TAs/devs trial any course/exercise/prompt without touching the production database.

<!--
Cover the "rationale for major implementation choices" action item. Keep each to one why.
-->

---

## AskTIM usage results — 11.270x (first week live)

*From the 06/09/2026 meeting notes. Live conversation logs are stored on Railway (not in the repo).*

- **4 unique AskTIM conversations** this week.
- **All 4 were logistics**, not content — students asked **how to submit the table** for the Power/Actor Map assignment, not about the substance of the exercise.
- The tutor **responded appropriately** given the nature of those questions.
- Read: current exercises may still be **too elementary** for students to lean on the tutor for conceptual help.
- **Reach:** ~15 verified + ~100 audit learners; ~**20–25 active**. Announced via **pinned course announcement + email**, linked from the Assignment 4 "Power/Actor Map Instructions" page.

<!--
Honest framing: usage is early and logistical, but it shows the tutor is functioning correctly
and reachable. Decision from 06/09: use these as evidence the tutor works, even if usage is light.
-->

---

## What we learned from early deployment

- The tutor **behaves correctly in the wild** — it handled real student questions appropriately on first contact.
- **Access path matters**: usage tracks how prominently AskTIM is surfaced (announcement + assignment-page link).
- **Assignment difficulty drives tutor value**: logistical-only questions suggest we need richer / harder exercises (and richer context) for the tutor to show its pedagogical strength.
- Validates the decision to **test across more courses** before broader rollout.

<!--
Source: 06/09/2026 "Decisions". Connect early usage → motivation for next steps.
-->

---

## Additional course testing (in progress this week)

- Goal: see how the tutor behaves **across different subjects and contexts**, not just climate/urban studies.
- Added and tested new course contexts spanning **STEM and humanities**:
  - Mathematics for Computer Science, Physics III (Vibrations & Waves) — STEM
  - The Meaning of Life, Intro to International Development Planning — humanities
- Method (per 06/09 notes): **student-persona simulations + the judge/evaluator framework**, plus **manual hand-testing**.
- Personas are kept as a **sanity check for edge cases**; we plan to make them less repetitive by reviewing recent work on LLM-based student simulation.

<!--
These runs can serve as live demos/evidence in the meeting. Generation + Claude judging (judge_08
/ rubric_08) already run across the new courses.
-->

---

## Proposed next steps

**Tutor development & expansion** *(06/09/2026 priorities)*

- **Richer context for the tutor:**
  - Accept **images as input** (students attaching figures; tutor reading exercise diagrams).
  - Reason over / produce **image-based outputs** where relevant.
  - Add **lecture transcripts** to the tutor's context — key for diagram- and lecture-heavy courses.
- **Better evaluation:**
  - Improve student personas (reduce repetitiveness) using recent LLM-student-simulation papers.
  - Continue manual hand-testing alongside simulated runs.
- **Internal tooling (lower priority):**
  - A small interface to **review real AskTIM conversations** without digging through Railway — easier to review, share, and analyze real student interactions.

<!--
Covers "proposed next steps for tutor development and expansion." Images + lecture transcripts
are the headline asks; persona improvement + a data-review UI round it out.
-->

---

## Summary

- AskTIM is **live in 11.270x** and behaving correctly on first real usage.
- It's backed by a **reproducible build → simulate → judge → review** pipeline that lets us iterate safely.
- Early usage is **light and logistical** → motivates richer exercises, richer context, and broader course testing.
- Next phase: **images + lecture transcripts in context**, **stronger student simulation**, and a **lightweight data-review tool**.

**Appendix available on request:** workflow diagram, example persona prompts, sample graded transcripts, the rubric.

<!--
Sources: meeting_notes/06_09_2026.md (primary), 03_20_2026.md (rubric/judge history),
README.md & memory/project_overview.md (architecture). Real 11.270x logs live on Railway.
-->
