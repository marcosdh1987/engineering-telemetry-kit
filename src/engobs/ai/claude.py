from __future__ import annotations

import json
from pathlib import Path
from typing import IO, Any, cast

# Claude Code hooks schema: hooks.<Event> is a list of matcher groups, each holding
# {"type": "command", "command": ...} handlers. The session id is delivered to the command as
# JSON on stdin (there is no CLAUDE_SESSION_ID environment variable), so the ai-session
# commands read it from there. Commands end with "|| true" so telemetry never blocks a turn.
MANAGED_COMMAND_PREFIX = "engobs "
HOOK_TIMEOUT_SECONDS = 15
COMMANDS = {
    "SessionStart": "engobs ai-session start --tool claude || true",
    "Stop": "engobs snapshot --trigger ai_turn || true",
    "SessionEnd": "engobs ai-session end --tool claude || true",
}
MATCHERS = {"SessionStart": "startup|resume"}
# Entries written by engobs < 0.1.1 (invalid for Claude Code); migrated on install/uninstall.
LEGACY_HOOK_IDS = {"engobs-session-start", "engobs-snapshot", "engobs-session-end"}


def managed_hook_group(event_name: str) -> dict[str, Any]:
    group: dict[str, Any] = {
        "hooks": [
            {
                "type": "command",
                "command": COMMANDS[event_name],
                "timeout": HOOK_TIMEOUT_SECONDS,
            }
        ]
    }
    if event_name in MATCHERS:
        group["matcher"] = MATCHERS[event_name]
    return group


def is_managed_group(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if item.get("managed_by") == "engobs" or item.get("id") in LEGACY_HOOK_IDS:
        return True
    handlers = item.get("hooks")
    if not isinstance(handlers, list) or not handlers:
        return False
    return all(
        isinstance(handler, dict)
        and handler.get("type") == "command"
        and str(handler.get("command", "")).startswith(MANAGED_COMMAND_PREFIX)
        for handler in handlers
    )


def read_hook_session_id(stream: IO[str]) -> str | None:
    """Session id from the JSON Claude Code pipes to hook commands; None when absent."""
    if stream.isatty():
        return None
    try:
        payload = json.loads(stream.read() or "{}")
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    session_id = payload.get("session_id")
    return str(session_id) if session_id else None


def claude_settings_path(repo_root: Path) -> Path:
    return repo_root / ".claude" / "settings.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return cast(dict[str, Any], json.loads(path.read_text()))


def install_claude_hooks(repo_root: Path) -> bool:
    path = claude_settings_path(repo_root)
    existed = path.exists()
    data = _load(path)
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return False
    changed = False
    for event_name in COMMANDS:
        event_hooks = hooks.setdefault(event_name, [])
        if not isinstance(event_hooks, list):
            continue
        desired = managed_hook_group(event_name)
        kept = [item for item in event_hooks if not is_managed_group(item)]
        managed = [item for item in event_hooks if is_managed_group(item)]
        if managed == [desired]:
            continue
        hooks[event_name] = [*kept, desired]
        changed = True
    if changed or not existed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path.exists()


def claude_hooks_installed(repo_root: Path) -> bool:
    path = claude_settings_path(repo_root)
    if not path.exists():
        return False
    data = _load(path)
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        return False
    for event_name in COMMANDS:
        event_hooks = hooks.get(event_name, [])
        if not isinstance(event_hooks, list):
            return False
        if managed_hook_group(event_name) not in event_hooks:
            return False
    return True


def uninstall_claude_hooks(repo_root: Path) -> None:
    path = claude_settings_path(repo_root)
    if not path.exists():
        return
    data = _load(path)
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return
    changed = False
    for event_name in COMMANDS:
        event_hooks = hooks.get(event_name)
        if not isinstance(event_hooks, list):
            continue
        filtered = [item for item in event_hooks if not is_managed_group(item)]
        if filtered != event_hooks:
            hooks[event_name] = filtered
            changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
