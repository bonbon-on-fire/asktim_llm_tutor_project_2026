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

- Each course is a subfolder (for example `philosophy/`, `urban_studies/`).
- `course.txt` stores shared course context.
- `exercise_XX.txt` stores the assignment prompt for a specific exercise.

## Available courses

| Folder | Course | Exercises |
| ------ | ------ | --------- |
| `philosophy/` | Philosophy (ethics, moral reasoning) | 1 — trolley problem / act consequentialism |
| `urban_studies/` | Urban Studies 11.024x (climate action) | 3 — geographic data, stressors, decision actors |

## Adding a new course

1. Create a folder under `curriculum/` with the course name.
2. Add `course.txt` with shared context.
3. Add one or more `exercise_XX.txt` files (zero-padded numbering).

## Adding an exercise to an existing course

Add a new `exercise_XX.txt` file in the course folder.
