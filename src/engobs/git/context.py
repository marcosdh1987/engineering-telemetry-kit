from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class GitError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitSnapshot:
    repo_root: Path
    organization: str | None
    project: str | None
    repository: str | None
    branch: str
    git_head_sha: str
    git_base_sha: str | None
    commits_count: int
    new_commits: int
    files_changed_count: int
    lines_added: int
    lines_deleted: int
    dirty_files_count: int
    untracked_files_count: int
    dirty_lines_added: int
    dirty_lines_deleted: int
    is_trunk: bool
    remote_name: str | None = None


TRUNK_BRANCHES = {"main", "master", "develop"}


def run_git(repo_root: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise GitError(completed.stderr.strip() or completed.stdout.strip() or "git command failed")
    return completed.stdout.strip()


def is_git_repo(repo_root: Path) -> bool:
    try:
        run_git(repo_root, "rev-parse", "--show-toplevel")
    except GitError:
        return False
    return True


def infer_identity_from_remote(remote_url: str) -> tuple[str | None, str | None]:
    if not remote_url:
        return None, None
    cleaned = remote_url.strip()
    if cleaned.startswith("git@") and ":" in cleaned:
        _, remainder = cleaned.split(":", 1)
        parts = [part for part in remainder.removesuffix(".git").split("/") if part]
    else:
        parsed = urlparse(cleaned)
        parts = [part for part in parsed.path.removesuffix(".git").split("/") if part]
    if len(parts) < 2:
        return None, None
    return parts[-2], parts[-1]


def _existing_refs(repo_root: Path, refs: Iterable[str]) -> str | None:
    for ref in refs:
        result = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", ref],
            cwd=repo_root,
            check=False,
        )
        if result.returncode == 0:
            return ref
    return None


def default_base_ref(repo_root: Path) -> str | None:
    origin_head = run_git(repo_root, "symbolic-ref", "refs/remotes/origin/HEAD", check=False)
    if origin_head:
        return origin_head
    return _existing_refs(
        repo_root,
        [
            "refs/remotes/origin/main",
            "refs/remotes/origin/master",
            "refs/remotes/origin/develop",
            "refs/heads/main",
            "refs/heads/master",
            "refs/heads/develop",
        ],
    )


def _parse_numstat(output: str) -> tuple[int, int, int]:
    files_changed = 0
    lines_added = 0
    lines_deleted = 0
    for line in output.splitlines():
        if not line.strip():
            continue
        added, deleted, *_ = line.split("	")
        if added != "-":
            lines_added += int(added)
        if deleted != "-":
            lines_deleted += int(deleted)
        files_changed += 1
    return files_changed, lines_added, lines_deleted


def get_snapshot(repo_root: Path) -> GitSnapshot:
    if not is_git_repo(repo_root):
        raise GitError("Not a Git repository")

    top_level = Path(run_git(repo_root, "rev-parse", "--show-toplevel"))
    branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    head_sha = run_git(repo_root, "rev-parse", "HEAD")
    remote_name = run_git(top_level, "remote", check=False).splitlines()[:1]
    remote_url = (
        run_git(top_level, "remote", "get-url", remote_name[0], check=False) if remote_name else ""
    )
    organization, repository = infer_identity_from_remote(remote_url)
    project = repository

    base_ref = default_base_ref(top_level)
    base_sha: str | None = None
    commits_count = 0
    files_changed_count = 0
    lines_added = 0
    lines_deleted = 0
    if base_ref:
        base_sha_candidate = run_git(top_level, "merge-base", head_sha, base_ref, check=False)
        if base_sha_candidate:
            base_sha = base_sha_candidate
            rev_range = f"{base_sha}..{head_sha}"
            commits_count = int(run_git(top_level, "rev-list", "--count", rev_range))
            files_changed_count, lines_added, lines_deleted = _parse_numstat(
                run_git(top_level, "diff", "--numstat", rev_range)
            )

    status_output = run_git(top_level, "status", "--porcelain")
    dirty_files = 0
    untracked_files = 0
    for line in status_output.splitlines():
        if not line:
            continue
        if line.startswith("??"):
            untracked_files += 1
        else:
            dirty_files += 1
    _, dirty_added, dirty_deleted = _parse_numstat(run_git(top_level, "diff", "--numstat", "HEAD"))

    return GitSnapshot(
        repo_root=top_level,
        organization=organization,
        project=project,
        repository=repository,
        branch=branch,
        git_head_sha=head_sha,
        git_base_sha=base_sha,
        commits_count=commits_count,
        new_commits=commits_count,
        files_changed_count=files_changed_count,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        dirty_files_count=dirty_files,
        untracked_files_count=untracked_files,
        dirty_lines_added=dirty_added,
        dirty_lines_deleted=dirty_deleted,
        is_trunk=branch in TRUNK_BRANCHES,
        remote_name=remote_name[0] if remote_name else None,
    )
