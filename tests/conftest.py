from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from engobs.config.loader import ENV_MAP

REMOTE_URL = "git@github.com:marcosdh1987/engineering-telemetry-kit.git"


def init_git_repo(path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True)

    git("init", "-b", "main")
    git("config", "user.name", "Tester")
    git("config", "user.email", "tester@example.com")
    (path / "README.md").write_text("hi\n")
    git("add", "README.md")
    git("commit", "-m", "init")
    git("remote", "add", "origin", REMOTE_URL)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo)
    return repo


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """No ENGOBS_* env vars and an empty XDG config home, so only repo config applies."""
    for name in ENV_MAP:
        monkeypatch.delenv(name, raising=False)
    xdg = tmp_path / "xdg"
    xdg.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return xdg / "engobs" / "config.toml"
