#!/usr/bin/env bash
# Stop nudge (non-blocking). If src/, tests/ or pyproject.toml have uncommitted changes, print
# a reminder to verify and compound. Runs nothing, mutates nothing, always exits 0.
set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

changed="$(git status --porcelain -- src tests pyproject.toml 2>/dev/null || true)"
if [ -z "$changed" ]; then
  exit 0
fi

cat <<'MSG'
Reminder (uncommitted changes in src/, tests/ or pyproject.toml):
  - Verify: make check (/verify) and report the result.
  - Docs: behavior changes ship with a docs/ update.
  - Compound: /retro for learnings (memory/), /adr for hard-to-reverse decisions.
  - Do not commit; leave changes unstaged for the maintainer.
MSG

exit 0
