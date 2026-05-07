# Curriculum

Assignment content used by tutor and student runs, organized by course.

## Structure

```text
curriculum/
  <course_name>/
    course.txt           # shared course context
    exercise_01.txt      # assignment prompt
    exercise_02.txt
    ...
```

- Each course is a subfolder (for example `philosophy/`, `cities_and_climate_change/`).
- `course.txt` stores shared course context.
- `exercise_XX.txt` stores the assignment prompt for a specific exercise.

## Available courses

| Folder | Course | Exercises |
| ------ | ------ | --------- |
| `philosophy/` | Philosophy (ethics, moral reasoning) | 1 — trolley problem / act consequentialism |
| `cities_and_climate_change/` | Cities and Climate Change: Mitigation and Adaptation (I, II and III) | 12 — case study city research + mitigation/adaptation planning |

## Adding a new course

1. Create a folder under `curriculum/` with the course name.
2. Add `course.txt` with shared context.
3. Add one or more `exercise_XX.txt` files (zero-padded numbering).

## Adding an exercise to an existing course

Add a new `exercise_XX.txt` file in the course folder.
