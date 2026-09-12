from __future__ import annotations

import os
from pathlib import Path

from engobs.ai.claude import install_claude_hooks
from engobs.commands.doctor import run_doctor
from engobs.commands.snapshot import run_snapshot
from engobs.config.loader import default_global_config_path, ensure_privacy_salt
from engobs.config.models import PrivacyMode
from engobs.git.context import get_snapshot
from engobs.git.hooks import HOOK_TRIGGERS, install_hook


def run_install(cwd: Path, *, profile: str | None) -> int:
    snapshot = get_snapshot(cwd)
    from engobs.commands.common import load_runtime_config

    config, repo_root = load_runtime_config(cwd, profile)
    if config.privacy_mode == PrivacyMode.STRICT and not config.privacy_salt:
        if os.environ.get("ENGOBS_PRIVACY_MODE", "").lower() == PrivacyMode.STRICT.value:
            print(
                "ERROR strict mode selected from environment requires ENGOBS_PRIVACY_SALT "
                "or a stored global privacy_salt"
            )
            return 1
        ensure_privacy_salt(default_global_config_path(), config.profile)
        config, repo_root = load_runtime_config(cwd, profile)

    for hook_name, trigger in HOOK_TRIGGERS.items():
        install_hook(repo_root, hook_name, trigger)
    install_claude_hooks(repo_root)
    run_snapshot(repo_root, profile=profile, trigger="manual", force=True)
    exit_code, _ = run_doctor(repo_root, profile=profile, emit_output=False)
    print(f"Installed engobs in {snapshot.repo_root}")
    print(f"Profile: {config.profile or 'default'}")
    print(f"Privacy mode: {config.privacy_mode.value}")
    print("Git hooks: post-commit, post-checkout")
    print("Claude hooks: managed if .claude/settings.json exists or is created")
    return exit_code
