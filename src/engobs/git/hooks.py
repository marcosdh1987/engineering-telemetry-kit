from __future__ import annotations

import os
from pathlib import Path

from engobs.git.context import run_git

START_MARKER = "# >>> engobs managed block >>>"
END_MARKER = "# <<< engobs managed block <<<"

HOOK_TRIGGERS = {
    "post-commit": "commit",
    "post-checkout": "checkout",
}


def git_dir(repo_root: Path) -> Path:
    resolved = Path(run_git(repo_root, "rev-parse", "--git-dir"))
    return resolved if resolved.is_absolute() else repo_root / resolved


def hook_file(repo_root: Path, hook_name: str) -> Path:
    return git_dir(repo_root) / "hooks" / hook_name


def managed_block(trigger: str) -> str:
    return "\n".join(
        [
            START_MARKER,
            "if command -v engobs >/dev/null 2>&1; then",
            f"  engobs snapshot --trigger {trigger} || true",
            "fi",
            END_MARKER,
        ]
    )


def install_hook(repo_root: Path, hook_name: str, trigger: str) -> None:
    path = hook_file(repo_root, hook_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    block = managed_block(trigger)
    if not path.exists():
        path.write_text(f"#!/bin/sh\n{block}\n")
        os.chmod(path, 0o755)
        return

    content = path.read_text()
    if START_MARKER in content:
        start = content.index(START_MARKER)
        end = content.index(END_MARKER) + len(END_MARKER)
        updated = content[:start].rstrip() + "\n" + block + content[end:]
        path.write_text(updated.rstrip() + "\n")
        os.chmod(path, 0o755)
        return
    separator = "\n" if content.endswith("\n") else "\n\n"
    path.write_text(content + separator + block + "\n")
    os.chmod(path, 0o755)


def hook_installed(repo_root: Path, hook_name: str) -> bool:
    path = hook_file(repo_root, hook_name)
    return path.exists() and START_MARKER in path.read_text()


def uninstall_hook(repo_root: Path, hook_name: str) -> None:
    path = hook_file(repo_root, hook_name)
    if not path.exists():
        return
    content = path.read_text()
    if START_MARKER not in content:
        return
    start = content.index(START_MARKER)
    end = content.index(END_MARKER) + len(END_MARKER)
    new_content = (content[:start] + content[end:]).strip()
    if new_content in {"", "#!/bin/sh"}:
        path.unlink()
        return
    path.write_text(new_content + "\n")
    os.chmod(path, 0o755)
