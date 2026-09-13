---
description: Close out work with a short retrospective and update project memory.
allowed-tools: Read, Edit, Write, Bash(git diff:*), Bash(git log:*), Bash(git status:*)
---

Run a brief retrospective on this session's work and persist what is worth keeping.

1. Review what changed (`git status`, `git diff`, the conversation).
2. Identify durable, non-obvious knowledge: gotchas, dead ends, why a choice was made.
   Skip anything obvious from the code, README, or git history.
3. Append entries to `memory/learnings.md` (dated, one fact each, format in `memory/README.md`)
   and update `memory/context.md` (active focus, open threads).
4. If a hard-to-reverse decision was made, suggest `/adr`.
5. Summarize what you recorded in 3-5 bullets. Do not commit.
