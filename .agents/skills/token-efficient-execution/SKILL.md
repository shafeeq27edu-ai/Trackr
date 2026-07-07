---
name: token-efficient-execution
description: Rules for minimizing token/context usage during coding tasks — targeted reads, diff-based edits, no redundant restating. Triggers on any file read, file edit, or multi-turn coding session.
---

# Token-Efficient Execution

## Reading files
- Never dump an entire file into context if only a function/section is
  relevant. Search/grep for the symbol or section first, then read only
  that range.
- Don't re-read a file you already have in context this session unless it
  was edited since — track what you've already seen instead of re-fetching.
- For large data files (videos, logs, model weights), never load contents
  into context — reference the path and use scripts/tools to inspect
  (e.g. print shape/head of a CSV, first N frames of a video) rather than
  reading raw bytes.

## Writing/editing files
- Prefer targeted diffs/patches over rewriting whole files, especially for
  files over ~50 lines.
- Batch related changes to the same file into one edit pass instead of
  multiple sequential small edits.
- When generating boilerplate (e.g. a new module under `tracker/`), write it
  directly rather than first describing it in prose and then writing it —
  pick one.

## Conversation output
- Don't restate AGENTS.md content, the build order, or the tech stack —
  reference "per AGENTS.md" instead of re-printing it.
- Don't paste full stack traces or logs back verbatim if only one line is
  the actual error — quote the relevant line(s) only.
- Status updates after a step should be 1–3 lines, not a full recap of what
  was already planned.

## Tool calls
- Don't fetch docs/web content for things already encoded in the
  `cv-tracking-standards` skill (YOLO output format, ByteTrack matching
  logic, etc.) — that skill is the reference; only search the web for
  something genuinely outside it (e.g. a library version bug).
- Run tests/lints in a single batched command where possible instead of
  one command per file.

## Rule of thumb
Before any read or output, ask: "does the agent (or the user) actually need
this much detail to proceed, or would a pointer/summary do?" Default to the
smaller option.
