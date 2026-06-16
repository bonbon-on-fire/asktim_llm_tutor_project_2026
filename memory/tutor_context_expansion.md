---
name: tutor-context-expansion
description: The unbuilt multimodal + lecture-transcript context work — current headline next build
metadata:
  type: project
---

The most concrete open build (06/09/2026 meeting + PLANNING Phases 6/7). Tutor/student/judge are currently **text-only**; `main_ui` passes only prose exercise descriptions even when a real figure exists.

**Three goals:**
1. Accept images as input (students attaching figures; tutor receiving curriculum figures).
2. Reason over / produce image-based outputs where relevant.
3. Add lecture transcripts as part of tutor context.

**Already on disk but unread:** figure PNGs live under `curriculum/<course>/figures/` (convention `exercise_<NN>_<desc>.{png,jpg,jpeg}`), documented in `curriculum/README.md`. Nothing reads them yet.

**Phase 6 plan (NOT STARTED):** new `utils/figures.py` (`discover_figures`, `image_to_data_url`, `build_multimodal_content`) feeding tutor/student/judge via LangChain normalized multimodal content (works for both GPT and Claude). Additive transcript `figures` field. Phase 7 = per-message human uploads in the chat composer (now lands in the Sandbox composer, not the old config panel). main_ui Step 10 (image uploads) is blocked on Phase 6.

**Why:** Important for courses where diagrams/visuals/lecture-specific explanations matter; the immediate cases are exercise_04 (Power/Actors Map) and exercise_08 (Spider Diagram) in cities_and_climate_change.

**How to apply:** When this work starts, build `utils/figures.py` first (mirror the `utils/parsing.py` pattern), then thread `figures` through tutor → student → judge. Lecture-transcript context is a newer ask not yet specced in PLANNING. See [[project-active-items]].
