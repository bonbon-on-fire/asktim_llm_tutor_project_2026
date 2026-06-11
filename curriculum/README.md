# Curriculum

Assignment content used by tutor and student runs, organized by course.

## Structure

```text
curriculum/
  <course_name>/
    course.txt                       # shared course context
    course_name.txt                  # display name shown in the main_ui course banner
    syllabus.txt                     # optional — appended to assignment text in main_ui
    exercise_01.txt                  # assignment prompt
    exercise_02.txt
    ...
    figures/
      exercise_04_power_actors_map.png   # naming: exercise_<NN>_<slug>.png
      ...
```

- Each course is a subfolder (for example `cities_and_climate_change/`, `mathematics_for_cs/`).
- `course.txt` stores shared course context.
- `course_name.txt` holds the human-readable course title rendered in the `main_ui/` course banner (via `load_course_name()` in [main_ui/routes/_validation.py](../main_ui/routes/_validation.py)). If empty or absent, the banner renders blank.
- `syllabus.txt` (optional) is appended to the assignment block in `main_ui/`'s context build (see [main_ui/services/tutor_bridge.py](../main_ui/services/tutor_bridge.py)).
- `exercise_XX.txt` stores the assignment prompt for a specific exercise.
- `figures/` holds visual context that belongs to a specific exercise. Files must start with `exercise_<NN>_` so the framework (Phase 6 — see root [PLANNING.md](../PLANNING.md)) can attach the matching figures when the tutor sees that exercise.

## Available courses

| Folder | Course | Exercises |
| ------ | ------ | --------- |
| `cities_and_climate_change/` | Cities and Climate Change: Mitigation and Adaptation (MIT 11.270x) | 12 — case study city research + mitigation/adaptation planning; **live in AskTIM for Spring 2026** |
| `intro_to_international_development_planning/` | Introduction to International Development Planning (MIT 11.701) | 24 — 700–800 word reflection prompts |
| `mathematics_for_cs/` | Mathematics for Computer Science (MIT 6.1200J) | 10 — discrete-math problem sets |
| `physics_iii_vibrations_and_waves/` | Physics III: Vibrations and Waves (MIT 8.03SC) | 10 — vibrations/waves problem sets |
| `meaning_of_life/` | The Meaning of Life (MIT 21A.157) | 3 — vignette + investigation + final reflection papers |

The four courses beyond Cities and Climate Change were added in June 2026 as **cross-course test contexts** (two STEM, two humanities) to check how the tutor behaves across subjects. Only `cities_and_climate_change/` is deployed to real students.

## Adding a new course

1. Create a folder under `curriculum/` with the course name.
2. Add `course.txt` with shared context, and `course_name.txt` with the display title for the banner.
3. Optionally add `syllabus.txt` for course-level material that should accompany every exercise.
4. Add one or more `exercise_XX.txt` files (zero-padded numbering).
5. If an exercise references diagrams or maps, drop them in `figures/` with the `exercise_<NN>_<slug>.<ext>` naming convention.

## Adding an exercise to an existing course

Add a new `exercise_XX.txt` file in the course folder. If it has visuals, add matching `figures/exercise_<NN>_*.png` files.
