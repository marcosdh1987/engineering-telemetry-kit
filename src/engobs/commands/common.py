from __future__ import annotations

import logging
from pathlib import Path

from engobs.config.loader import load_config
from engobs.config.models import PrivacyMode, ResolvedConfig
from engobs.git.context import get_snapshot


class CommandWarning(UserWarning):
    pass


def configure_logging(debug: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO, format="%(message)s")


def repo_root_from_cwd(cwd: Path) -> Path:
    snapshot = get_snapshot(cwd)
    return snapshot.repo_root


def load_runtime_config(cwd: Path, profile: str | None = None) -> tuple[ResolvedConfig, Path]:
    repo_root = repo_root_from_cwd(cwd)
    config = load_config(repo_root, profile_override=profile)
    return config, repo_root


def strict_mode_ready(config: ResolvedConfig) -> bool:
    return not (config.privacy_mode == PrivacyMode.STRICT and not config.privacy_salt)
