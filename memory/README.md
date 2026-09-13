# Project memory

Durable, human-readable working memory for this repository. Agents and humans read these files
at the start of work (`AGENTS.md` section 4) and append to them when they learn something worth
keeping. Every substantive session should leave the memory slightly richer than it found it.

Memory is for *operational, project-specific* knowledge that is not obvious from the code, the
README, or git history. Do not duplicate those here.

| File | Holds | Update when |
| --- | --- | --- |
| `context.md` | Current state: active focus, constraints in force, open threads. | Start/end of a session, or when the focus shifts. |
| `learnings.md` | Non-obvious facts: gotchas, dead ends, why something is the way it is. | The moment you learn something that would have saved you time. |

## Entry format

```markdown
## <short title> — <YYYY-MM-DD>

<one or two sentences of fact>

**Why it matters:** <the consequence>
**How to apply:** <what to do next time>
```

Guidelines: one fact per entry (split if it grows); absolute dates; delete entries that turn out
to be wrong instead of leaving them to mislead; link related ADRs in `docs/adr/`; in Claude
Code, `/retro` walks through this at the end of a session.
