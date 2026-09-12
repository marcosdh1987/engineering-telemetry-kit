from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

MANAGED_HOOK_IDS = {
    "SessionStart": "engobs-session-start",
    "Stop": "engobs-snapshot",
    "SessionEnd": "engobs-session-end",
}

SESSION_START_COMMAND = (
    'engobs ai-session start --tool claude --session-id "${CLAUDE_SESSION_ID:-unknown}"'
)
SESSION_END_COMMAND = (
    'engobs ai-session end --tool claude --session-id "${CLAUDE_SESSION_ID:-unknown}"'
)
COMMANDS = {
    "SessionStart": SESSION_START_COMMAND,
    "Stop": "engobs snapshot --trigger ai_turn",
    "SessionEnd": SESSION_END_COMMAND,
}


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
    changed = False
    for event_name, hook_id in MANAGED_HOOK_IDS.items():
        event_hooks = hooks.setdefault(event_name, [])
        if not isinstance(event_hooks, list):
            continue
        already_present = any(
            isinstance(item, dict) and item.get("id") == hook_id for item in event_hooks
        )
        if already_present:
            continue
        event_hooks.append(
            {
                "id": hook_id,
                "command": COMMANDS[event_name],
                "managed_by": "engobs",
            }
        )
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
    for event_name, hook_id in MANAGED_HOOK_IDS.items():
        event_hooks = hooks.get(event_name, [])
        installed = any(
            isinstance(item, dict) and item.get("id") == hook_id for item in event_hooks
        )
        if not installed:
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
    for event_name, hook_id in MANAGED_HOOK_IDS.items():
        event_hooks = hooks.get(event_name)
        if not isinstance(event_hooks, list):
            continue
        filtered = [
            item
            for item in event_hooks
            if not (isinstance(item, dict) and item.get("id") == hook_id)
        ]
        if filtered != event_hooks:
            hooks[event_name] = filtered
            changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
