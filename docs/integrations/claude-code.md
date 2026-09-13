# Claude Code integration

`engobs install` inserts managed hook groups into `.claude/settings.json` of the target
repository (creating the file if needed) and preserves everything else in it:

| Event | Matcher | Command |
| --- | --- | --- |
| `SessionStart` | `startup\|resume` | `engobs ai-session start --tool claude \|\| true` |
| `Stop` | all | `engobs snapshot --trigger ai_turn \|\| true` |
| `SessionEnd` | all | `engobs ai-session end --tool claude \|\| true` |

Entries follow the Claude Code hooks schema (`{"matcher", "hooks": [{"type": "command",
"command", "timeout"}]}`). The session id is read from the JSON that Claude Code pipes to the
hook on stdin and is pseudonymized before it is sent. `|| true` keeps telemetry from ever
blocking a turn. Restart Claude Code (or start a new session) after `engobs install` so the
hooks are loaded.

`engobs uninstall` removes only the engobs-managed groups. Entries written by engobs < 0.1.1
used an invalid shape and never fired; running `engobs install` again migrates them.
