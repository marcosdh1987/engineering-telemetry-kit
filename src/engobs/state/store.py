from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from engobs.git.context import run_git


def state_dir(repo_root: Path) -> Path:
    git_dir = Path(run_git(repo_root, "rev-parse", "--git-dir"))
    resolved = git_dir if git_dir.is_absolute() else repo_root / git_dir
    return resolved / "engobs"


def state_path(repo_root: Path) -> Path:
    return state_dir(repo_root) / "state.json"


def load_state(repo_root: Path) -> dict[str, Any]:
    path = state_path(repo_root)
    if not path.exists():
        return {}
    return cast(dict[str, Any], json.loads(path.read_text()))


def save_state(repo_root: Path, state: dict[str, Any]) -> None:
    path = state_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def next_verification_attempt(repo_root: Path) -> int:
    state = load_state(repo_root)
    attempts = int(state.get("verification_attempt", 0)) + 1
    state["verification_attempt"] = attempts
    save_state(repo_root, state)
    return attempts


def should_emit_heartbeat(
    repo_root: Path,
    key: str,
    occurred_at_epoch: int,
    heartbeat_seconds: int,
) -> bool:
    state = load_state(repo_root)
    heartbeat_state = state.setdefault("heartbeats", {})
    last_seen = int(heartbeat_state.get(key, 0))
    if occurred_at_epoch - last_seen < heartbeat_seconds:
        return False
    heartbeat_state[key] = occurred_at_epoch
    save_state(repo_root, state)
    return True


def update_snapshot_fingerprint(repo_root: Path, fingerprint: str, occurred_at: str) -> None:
    state = load_state(repo_root)
    state["last_snapshot_fingerprint"] = fingerprint
    state["last_activity_timestamp"] = occurred_at
    save_state(repo_root, state)


def set_ai_session_state(repo_root: Path, tool: str, session_id: str, active: bool) -> None:
    state = load_state(repo_root)
    ai_state = state.setdefault("ai_sessions", {})
    ai_state[f"{tool}:{session_id}"] = {"active": active}
    save_state(repo_root, state)


def clear_local_state(repo_root: Path) -> None:
    directory = state_dir(repo_root)
    if not directory.exists():
        return
    for path in sorted(directory.glob("**/*"), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()
    if directory.exists():
        directory.rmdir()
