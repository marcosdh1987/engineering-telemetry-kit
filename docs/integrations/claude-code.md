# Claude Code integration

`engobs install` detects `.claude/settings.json` in the target repository and preserves existing settings while inserting only managed hook entries for:

- `SessionStart` -> `engobs ai-session start --tool claude --session-id ...`
- `Stop` -> `engobs snapshot --trigger ai_turn`
- `SessionEnd` -> `engobs ai-session end --tool claude --session-id ...`

`engobs uninstall` removes only the managed entries and preserves everything else.
