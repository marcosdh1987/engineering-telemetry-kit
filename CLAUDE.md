@AGENTS.md

## Claude Code specifics

- Slash commands: `/plan` (ground + plan, no code), `/verify` (`make check`, read-only),
  `/retro` (persist learnings to `memory/`), `/adr` (scaffold a decision record).
  Use the built-in `/code-review` before declaring a change ready.
- `.claude/settings.json` hooks are non-blocking nudges (SessionStart reminder, Stop reminder
  when `src/`/`tests/` are dirty). They never run tests or mutate files.
- `git commit`/`push`/`merge`/`rebase` prompt for permission by design; the maintainer commits.
- `engobs install` run inside this repo appends engobs-managed hook entries to the tracked
  `.claude/settings.json`; do not commit those entries.
