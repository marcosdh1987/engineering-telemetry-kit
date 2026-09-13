---
description: Scaffold a new Architecture Decision Record from the template.
argument-hint: <short decision title>
allowed-tools: Read, Write, Edit, Glob, Bash(ls:*)
---

Create an ADR for: **$ARGUMENTS**

1. Read `docs/adr/README.md` (trigger criteria) and `docs/adr/0000-template.md`.
2. Next number = highest existing `docs/adr/NNNN-*.md` + 1, zero-padded to 4 digits.
3. Create `docs/adr/<NNNN>-<kebab-title>.md` from the template: Context, Decision ("We will
   ..."), Consequences, Alternatives considered. Status `Proposed`, today's date.
4. Add it to the index in `docs/adr/README.md` (the harness test checks this).
5. Show the draft and list anything you had to assume.

Only for hard-to-reverse decisions; otherwise suggest a `memory/learnings.md` entry instead.
