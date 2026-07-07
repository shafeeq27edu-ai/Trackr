---
name: planning-protocol
description: Enforces plan-before-code discipline and step-gated execution for the object-tracker build order. Triggers on any request to build, add, implement, or extend a feature in this project.
---

# Planning Protocol

Use this skill whenever a request would involve writing or modifying code
for the object-tracker project.

## Before writing any code
1. Identify which build-order step (1–5, per AGENTS.md) the request belongs to.
2. If it spans multiple steps, split it — only execute the earliest unfinished step now.
3. Write a short plan artifact (bullet list, not prose) covering:
   - Files to be created/touched
   - The single acceptance check that proves this step works
     (e.g. "boxes render on 3 sample frames with correct class labels")
   - Any assumption being made in place of asking the user
4. Do not proceed to code until the plan is at most a few lines — if it's
   getting long, the scope is too big; shrink it to the current step only.

## Step gating
- Finish one build-order step, run/verify it, report the result briefly.
- Do NOT cascade into the next step automatically unless the user explicitly
  asked for the whole pipeline in one go AND confirmed that at the start.
- If the user says "build the whole thing," still stop and report after each
  step with a one-line status, rather than silently running steps 1–5 and
  dumping everything at once — this keeps review cheap and catches drift early.

## Re-planning
If a step fails its acceptance check, don't patch randomly. Re-state the
plan for that step only, with the fix, before touching code again.

## What NOT to do
- Don't write a full-project design doc for a one-file change.
- Don't re-explain the whole pipeline (it's already in AGENTS.md) — reference
  it, don't restate it.
- Don't ask the user clarifying questions that AGENTS.md already answers
  (tech stack, structure, build order are fixed — just proceed).
