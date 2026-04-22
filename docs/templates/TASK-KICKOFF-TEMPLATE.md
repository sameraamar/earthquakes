# Task Kickoff Template

## Purpose
Reusable prompt to start a new task with a fresh AI session.

## Maintenance
- Update only if the kickoff workflow itself changes.

---

## Use
Copy the block below, fill in `<TASK-ID>` and `<TASK TITLE>`, and paste into chat.

```
You are starting task <TASK-ID> — <TASK TITLE>.

1. Read these files in order:
   - docs/START_HERE.md
   - docs/tasks.md
   - docs/design/design.md
   - any relevant design subdocument

2. Summarize:
   - Current project intent and phase
   - This task's acceptance criteria
   - Any open dependencies or risks

3. Ask clarifying questions ONLY if necessary.

4. Propose a MINIMAL, reviewable implementation plan:
   - Files to add or change
   - Smallest possible diff
   - Validation steps

5. Wait for approval before editing code.
```
