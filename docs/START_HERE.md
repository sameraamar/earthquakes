# START HERE

## Purpose
Entrypoint for humans and AI agents joining this project.
Summarizes intent, current phase, and where the source of truth lives.

## Maintenance
- Updated by: Humans or AI when project phase or top-level intent changes.
- Relates to: every other doc; this file is the index.

---

## Project summary
Investigate a global earthquake dataset (1990–2023) to:
1. Understand patterns (geography, time, magnitude, depth).
2. Visualize earthquakes on an **interactive map** and **timeline** (HTML output).
3. Build a **baseline predictive model** for "next earthquake" indicators
   (region-level frequency / magnitude forecasting).

Goals will be refined as we discover the data.

## Target users
- The repo owner (data exploration / learning project).
- Future contributors / AI agents picking this up cold.

## Current phase
**Phase 1 — Bootstrap & data exploration.**

## Sources of truth
- [docs/tasks.md](tasks.md) — what to do, in what order.
- [docs/design/design.md](design/design.md) — how and why.
- [docs/decisions/](decisions/) — architecture decisions (ADRs).
- [docs/research/research-notes.md](research/research-notes.md) — findings.

## Restart an AI session
Paste this into chat:

> Read docs/START_HERE.md, then docs/tasks.md, then docs/design/design.md,
> then the relevant design subdocuments if they exist.
> Summarize the current project intent and phase.
> Ask clarifying questions ONLY if required.
> Then propose a minimal, reviewable implementation plan.

## Start a new task
Use [docs/templates/TASK-KICKOFF-TEMPLATE.md](templates/TASK-KICKOFF-TEMPLATE.md).

## Run the project
See [README.md](../README.md) for setup and run commands.
