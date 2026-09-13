"""Guards the Harness Lite (ADR-0004) against drift: governance files, ADR index, hooks."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

GOVERNANCE_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".github/architecture.md",
    ".github/standards.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "docs/development.md",
    "docs/adr/README.md",
    "docs/adr/0000-template.md",
    "memory/README.md",
    "memory/context.md",
    "memory/learnings.md",
)

# Privacy boundaries every agent must see on load (AGENTS.md section 2).
BOUNDARY_TERMS = (
    "source code",
    "diffs",
    "prompts",
    "developer name",
    "secrets",
    "terminal output",
    'extra="forbid"',
    "make check",
    "git commit",
)


@pytest.mark.parametrize("relative", GOVERNANCE_FILES)
def test_governance_file_exists(relative: str) -> None:
    assert (REPO_ROOT / relative).is_file(), relative


def test_claude_md_imports_canonical_agents_file() -> None:
    assert "@AGENTS.md" in (REPO_ROOT / "CLAUDE.md").read_text()


@pytest.mark.parametrize("term", BOUNDARY_TERMS)
def test_agents_md_states_boundaries_and_gate(term: str) -> None:
    assert term in (REPO_ROOT / "AGENTS.md").read_text(), term


def test_every_adr_is_indexed() -> None:
    index = (REPO_ROOT / "docs/adr/README.md").read_text()
    for adr in sorted((REPO_ROOT / "docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md")):
        if adr.name.startswith("0000-"):
            continue
        assert f"({adr.name})" in index, f"{adr.name} missing from docs/adr/README.md index"


def test_adr_numbers_are_unique() -> None:
    numbers = [path.name[:4] for path in (REPO_ROOT / "docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md")]
    assert len(numbers) == len(set(numbers)), numbers


def test_claude_hooks_reference_executable_scripts() -> None:
    settings = json.loads((REPO_ROOT / ".claude/settings.json").read_text())
    hook_events = settings["hooks"]
    assert set(hook_events) >= {"SessionStart", "Stop"}
    for entries in hook_events.values():
        for entry in entries:
            for hook in entry["hooks"]:
                assert hook["type"] == "command"
                match = re.search(r"\.claude/hooks/([A-Za-z0-9_]+\.sh)", hook["command"])
                assert match, hook["command"]
                script = REPO_ROOT / ".claude/hooks" / match.group(1)
                assert script.is_file(), script
                assert os.access(script, os.X_OK), f"{script} is not executable"
                assert "exit 0" in script.read_text(), "hooks must be non-blocking"


def test_git_mutations_require_permission() -> None:
    settings = json.loads((REPO_ROOT / ".claude/settings.json").read_text())
    ask = settings["permissions"]["ask"]
    assert "Bash(git commit:*)" in ask
    assert "Bash(git push:*)" in ask
