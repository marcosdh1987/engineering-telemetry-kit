from __future__ import annotations

from pathlib import Path

from engobs.ai.claude import uninstall_claude_hooks
from engobs.git.context import get_snapshot
from engobs.git.hooks import HOOK_TRIGGERS, uninstall_hook
from engobs.state.store import clear_local_state


def run_uninstall(cwd: Path, *, profile: str | None) -> int:
    del profile
    snapshot = get_snapshot(cwd)
    for hook_name in HOOK_TRIGGERS:
        uninstall_hook(snapshot.repo_root, hook_name)
    uninstall_claude_hooks(snapshot.repo_root)
    clear_local_state(snapshot.repo_root)
    print(f"Removed engobs-managed hooks from {snapshot.repo_root}")
    return 0
