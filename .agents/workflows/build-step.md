---
description: Execute exactly one step of the object-tracker build order (per AGENTS.md), verify it, and stop for review.
---

When the user types `/build-step` or `/build-step <n>`:

1. Determine the current step: if `<n>` is given, use it; otherwise infer the
   next unfinished step from what already exists in the project (e.g. if
   `tracker/detector.py` works but `tracker/tracker.py` doesn't exist yet,
   the current step is 2).
2. Apply the `planning-protocol` skill: write a short plan for this step only.
3. Apply `cv-tracking-standards` and `code-style` where relevant to the step.
4. Implement only this step's scope. Do not touch files belonging to later steps.
5. Run the step's acceptance check (see AGENTS.md build order) and report
   pass/fail in 1–3 lines.
6. Stop. Do not automatically continue to the next step — wait for the user
   to run `/build-step` again or explicitly say to continue.

This exists to prevent the agent from cascading through all 5 build steps
in one uninterrupted (and expensive) run, and to keep each step reviewable
and cheap to re-do if something's wrong.
