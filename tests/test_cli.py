import subprocess
from pathlib import Path
from typing import Any

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


def test_ai_session_reads_session_id_from_hook_stdin(
    git_repo: Path,
    isolated_config: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import io
    import sys

    from engobs.privacy.pseudonymize import opaque_session_id
    from engobs.transport.http import DeliveryResult

    sent: list[Any] = []

    def fake_send_event(config: Any, event: Any) -> DeliveryResult:
        sent.append(event)
        return DeliveryResult(ok=True, status_code=202, message="ok")

    monkeypatch.chdir(git_repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")
    monkeypatch.setattr("engobs.commands.ai_session.send_event", fake_send_event)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"session_id": "abc123", "cwd": "/x"}'))

    assert main(["ai-session", "start", "--tool", "claude"]) == 0

    (event,) = sent
    assert event.ai_tool == "claude"
    assert event.opaque_session_id == opaque_session_id("abc123")
    assert "abc123" not in event.model_dump_json()
