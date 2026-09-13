---
description: Ground in code and memory, then produce a plan before touching code.
argument-hint: <what you want to build or change>
allowed-tools: Read, Grep, Glob, Task
---

Produce a grounded plan for: **$ARGUMENTS**

1. **Ground.** Read `AGENTS.md` (boundaries in section 2), `memory/context.md`,
   `memory/learnings.md`, and the code and tests involved (Grep/Glob/Read or an Explore agent).
2. **Plan.** List ordered steps; for each: the files it touches and the exact verification
   command (focused `pytest` first, `make check` to close).
3. Call out assumptions and the most decision-changing open questions; ask before choosing.
4. Say whether the change needs an ADR (dependency, schema field, privacy/transport boundary,
   config semantics) or only a memory entry.
5. Do **not** write production code in this command; output the plan and wait for go.
