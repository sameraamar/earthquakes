# Copilot Repository Instructions

## Purpose
Always-on behavioral rules for AI agents working in this repository.
This file persists intent across AI sessions and ensures consistent, minimal,
documentation-first development.

## Maintenance
- Updated by: Humans or AI when project-wide rules change.
- Relates to: `docs/START_HERE.md`, `docs/tasks.md`, `docs/design/design.md`.

---

## Before ANY implementation work
1. Read [docs/START_HERE.md](../docs/START_HERE.md)
2. Read [docs/tasks.md](../docs/tasks.md)
3. Read [docs/design/design.md](../docs/design/design.md), then only the
   relevant design subdocuments if they exist.

## After ANY implementation work
- Update [docs/tasks.md](../docs/tasks.md) (status, completion, notes).
- Update [docs/design/design.md](../docs/design/design.md) and only the
  relevant design subdocuments when needed.
- Do not modify unrelated docs.

## Code Surgeon rules
- Make the smallest possible diff to satisfy the task.
- Never reformat unrelated code.
- Do not rename unless explicitly required.
- Preserve ordering, imports, whitespace, and comments.
- Maintain backward compatibility.

## Refactoring
- Refactoring is a separate task with its own clean, reviewable diff.

## Project-specific notes
- Domain: earthquake data exploration, visualization, and prediction.
- Primary dataset: Kaggle `alessandrolobello/the-ultimate-earthquake-dataset-from-1990-2023`.
- Language/stack: Python 3.11+, pandas, folium, plotly, scikit-learn.
- Tests live under `/tests/` (pytest). Add tests when behavior is non-trivial.
