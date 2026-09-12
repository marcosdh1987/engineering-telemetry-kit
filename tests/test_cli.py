import subprocess
from pathlib import Path

import pytest

from engobs.cli import main

REMOTE_URL = "git@github.com:marcosdh1987/engineering-telemetry-kit.git"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(path: Path) -> None:
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Tester")
    _git(path, "config", "user.email", "tester@example.com")
    (path / "README.md").write_text("hi\n")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "init")
    _git(path, "remote", "add", "origin", REMOTE_URL)


def test_verify_requires_command() -> None:
    with pytest.raises(SystemExit):
        main(["verify"])


def test_install_and_uninstall_manage_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "http://127.0.0.1:9")

    assert main(["install"]) == 0
    assert (repo / ".git" / "hooks" / "post-commit").exists()

    assert main(["uninstall"]) == 0
