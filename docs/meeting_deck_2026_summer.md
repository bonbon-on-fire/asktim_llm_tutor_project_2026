# AskTIM

## A Socratic LLM Tutor for MIT OpenCourseWare

- Project review — **June 2026**
- Nishita Bhakar · Romain Puech · Faizan Siddiqi

---

## What AskTIM is

- A **Socratic tutor** for MIT OCW assignments
- Guides students with questions — **never gives the answer**
- **Live now** in _MIT 11.270x — Cities & Climate Change_ (Spring 2026)
- Embedded in the MIT Learn assignment page (iframe chat)

---

## The challenge — and our approach

- **Hard part isn't the chatbot — it's _proving_ it stays in its role** with real students
- So the project is a **test-and-measure loop:**

> build/modify tutor → simulate conversations → AI judge grades them → read results → change one thing → repeat

- Once scores said it was reliable → **deploy + watch real usage**

---

## Timeline (Feb → June 2026)

- **Feb** — first tutor + adversarial student bots + grading rubric + judge
- **Mar** — automated test pipeline; dual GPT + Claude judges
- **Mar–Apr** — judge calibration → **picked Claude as grader**
- **Apr** — tutor prompt iteration → **`tutor_05`**
- **May** — web app: streaming, identity, history
- **Jun 1** — **deployed on Railway**
- **Spring** — **live in 11.270x**
- **Jun 9** — first real usage; expand testing to new courses
- **This week** — 4 new courses simulated + graded

---

## How we test the tutor

- **Student bots** — 18 personas in 3 families, each probes one failure mode:
  - **chaotic** → demands the answer / tries to jailbreak
  - **clueless** → plays lost, invites over-explaining
  - **cooperative** → sincere, well-meaning baseline
- **AI judge** grades every finished conversation against a fixed rubric
- **Run the matrix:** every persona × every exercise, scored automatically

---

## What the judge checks (rubric, plain English)

- Starts at full marks, **subtracts points for specific mistakes** — total **40**
- **Socratic (12 pts)** — avoid doing the student's work; **lose all 12 if it gives the answer**
- **Scaffolding (6)** — build on what they got right; diagnose confusion first
- **Meta-learning (2)** — coach _how_ to reason, not just right/wrong
- **No spiraling (4)** — don't loop without progress
- **On-assignment (8)** — keep them on task; redirect off-topic
- **Bite-sized (4)** — short, clear replies
- **Tone (4)** — encouraging coach, not a cold grader

---

## Making the judge trustworthy

- Test: **two AI judges (GPT + Claude) grade the same chats** — do they agree?
- Disagreement = the _rubric_ is ambiguous, not the tutor
- Fixed by **simplifying the rubric** (46 → **40 points**)
- **Claude was far more self-consistent (~0.8) than GPT**
- **Decision: Claude is the official judge; GPT dropped**

---

## Improving the tutor

- Built a **"fork-at-the-broken-turn" tool** → clean A/B test of a prompt tweak
- Ran **30 conversations: old wording vs new (`tutor_05`)**
- **Result: `tutor_05` lost _zero_ points for giving away the answer**
  - old version had been caught handing over fill-in-the-blank skeletons
- The never-give-the-answer guarantee **held**

---

## Results — the scoreboard

- **889 simulated conversations graded** (Claude judge, out of 40):
  - Mean **36.8 / 40**, median **38**
  - **49% scored a perfect 40**
  - Only **~1.7%** hit the big "did the student's work" penalty → **rare failure**
- By student type: **cooperative 39.5 · chaotic 36.3 · clueless 35.2**
  - (easiest → hardest to tutor, as expected)

---

## Human spot-check (honest read)

- Three of us **hand-graded the same 20 conversations**, compared to Claude
- **Moderate agreement:** Spearman **0.59** (Nishita), **0.57** (Romain)
- Claude's average (**31.8/40**) ≈ the **strictest** human grader
- Read: **Claude grades consistently, slightly strict** — good enough to _rank_ tutor versions
- Caveat: small sample (20); one grader's sheet was unfilled

---

## Live deployment + early usage (11.270x)

- Student web app on **Railway**: DB logging, iframe embed, email+password identity, streaming replies, chat history
- **~120 students** enrolled (8 for credit)
- **First week live: 4 conversations — all logistical** ("how do I submit the table?")
- Tutor handled them appropriately
- Read: early exercises **too elementary** to need conceptual help yet
- ~15 verified + ~100 audit learners; ~20–25 active

---

## Cross-course generalization (this week)

- Ran the same simulate-and-judge pipeline on **4 new courses** (2 STEM + 2 humanities)
- **414 conversations graded — mean 38.2 / 40, zero failures**
  - by course: math 38.3 · physics 38.3 · meaning-of-life 37.5 (**tightly clustered**)
- **432 more** generating now (Intl Development Planning)
- Shows the tutor **behaves consistently across very different subjects**

---

## What we learned

- The tutor **behaves correctly in the wild** on first real contact
- **Usage tracks how prominently it's surfaced** (announcement + assignment link)
- **Exercise difficulty drives value** — logistical-only questions → need richer/harder exercises
- Adversarial bots have **plateaued** → next real bugs come from **human testing**

---

## Proposed next steps

- **Richer tutor context:**
  - Accept **images** (student figures + exercise diagrams)
  - Add **lecture transcripts** to context
- **Better evaluation:**
  - Improve student personas (less repetitive) per recent LLM-simulation papers
  - More **human testing**
- **Internal tooling:** lightweight app to **review real conversations** (vs digging through Railway)

---

## Summary

- AskTIM is **live in 11.270x** and behaving correctly
- Backed by a **build → simulate → judge → review** loop with real numbers behind it
- **889 graded, mean 36.8/40, ~1.7% answer-giving failures**
- Early usage is **light + logistical** → motivates richer exercises, images, lecture context
- Next: **images + lecture transcripts**, stronger simulation, a data-review tool

<!-- Appendix on request: workflow diagram, persona prompts, sample graded transcripts, full rubric. Detail: meeting_notes/dimitris_process_detail.md -->
