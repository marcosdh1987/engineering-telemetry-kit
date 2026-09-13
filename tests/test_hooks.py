import io
import json
import subprocess
from pathlib import Path

from engobs.ai.claude import (
    COMMANDS,
    claude_hooks_installed,
    install_claude_hooks,
    managed_hook_group,
    read_hook_session_id,
    uninstall_claude_hooks,
)
from engobs.git.hooks import install_hook, managed_block, uninstall_hook


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(path: Path) -> None:
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Tester")
    _git(path, "config", "user.email", "tester@example.com")
    (path / "README.md").write_text("hi\n")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "init")


def test_hook_install_is_idempotent_and_preserves_existing_content(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\necho existing\n")

    install_hook(repo, "post-commit", "commit")
    install_hook(repo, "post-commit", "commit")

    content = hook.read_text()
    assert "echo existing" in content
    assert content.count("engobs snapshot --trigger commit || true") == 1

    uninstall_hook(repo, "post-commit")
    assert hook.read_text() == "#!/bin/sh\necho existing\n"


def test_hook_install_replaces_outdated_managed_block(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    hook = repo / ".git" / "hooks" / "post-commit"
    hook.write_text(
        "#!/bin/sh\n# >>> engobs managed block >>>\nlegacy\n# <<< engobs managed block <<<\n"
    )

    install_hook(repo, "post-commit", "commit")

    assert hook.read_text() == f"#!/bin/sh\n{managed_block('commit')}\n"


def test_claude_settings_are_preserved_and_uninstall_only_removes_managed_entries(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings_path = repo / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    custom = {"matcher": "startup", "hooks": [{"type": "command", "command": "echo hi"}]}
    settings_path.write_text(json.dumps({"theme": "dark", "hooks": {"SessionStart": [custom]}}))

    assert install_claude_hooks(repo)
    assert claude_hooks_installed(repo)
    data = json.loads(settings_path.read_text())
    assert data["theme"] == "dark"
    assert custom in data["hooks"]["SessionStart"]
    assert managed_hook_group("SessionStart") in data["hooks"]["SessionStart"]
    assert data["hooks"]["Stop"] == [managed_hook_group("Stop")]

    uninstall_claude_hooks(repo)
    data = json.loads(settings_path.read_text())
    assert data["theme"] == "dark"
    assert data["hooks"]["SessionStart"] == [custom]
    assert data["hooks"]["Stop"] == []


def test_claude_hook_groups_follow_claude_code_schema() -> None:
    for event_name in COMMANDS:
        group = managed_hook_group(event_name)
        assert set(group) <= {"matcher", "hooks"}
        (handler,) = group["hooks"]
        assert handler["type"] == "command"
        assert handler["command"].startswith("engobs ")
        assert handler["command"].endswith("|| true")  # never blocks the AI turn
        assert "CLAUDE_SESSION_ID" not in handler["command"]  # session id comes from stdin


def test_claude_install_is_idempotent_and_migrates_legacy_entries(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    settings_path = repo / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    legacy = {"id": "engobs-session-start", "command": "old", "managed_by": "engobs"}
    settings_path.write_text(json.dumps({"hooks": {"SessionStart": [legacy]}}))

    install_claude_hooks(repo)
    first = settings_path.read_text()
    install_claude_hooks(repo)

    assert settings_path.read_text() == first
    data = json.loads(first)
    assert data["hooks"]["SessionStart"] == [managed_hook_group("SessionStart")]


def test_read_hook_session_id_from_stdin_json() -> None:
    assert read_hook_session_id(io.StringIO('{"session_id": "abc123"}')) == "abc123"
    assert read_hook_session_id(io.StringIO("")) is None
    assert read_hook_session_id(io.StringIO("not json")) is None
