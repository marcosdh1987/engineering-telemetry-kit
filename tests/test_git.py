import subprocess
from pathlib import Path

from engobs.git.context import get_snapshot, infer_identity_from_remote

REMOTE_URL = "git@github.com:marcosdh1987/engineering-telemetry-kit.git"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_infer_identity_from_remote() -> None:
    assert infer_identity_from_remote("git@github.com:marcosdh1987/bot-trello-v1.git") == (
        "marcosdh1987",
        "bot-trello-v1",
    )
    assert infer_identity_from_remote("https://github.com/marcosdh1987/bot-trello-v1.git") == (
        "marcosdh1987",
        "bot-trello-v1",
    )


def test_git_snapshot_aggregates_without_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Tester")
    _git(repo, "config", "user.email", "tester@example.com")
    (repo / "README.md").write_text("hello\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "remote", "add", "origin", REMOTE_URL)
    _git(repo, "checkout", "-b", "feature/test")
    (repo / "README.md").write_text("hello\nworld\n")
    (repo / "draft.txt").write_text("draft\n")

    snapshot = get_snapshot(repo)

    assert snapshot.organization == "marcosdh1987"
    assert snapshot.repository == "engineering-telemetry-kit"
    assert snapshot.branch == "feature/test"
    assert snapshot.untracked_files_count == 1
    assert snapshot.dirty_files_count >= 1
    assert snapshot.dirty_lines_added >= 1
