---
description: Run the read-only quality gate and summarize results.
allowed-tools: Bash(make check:*), Bash(make lint:*), Bash(make typecheck:*), Bash(make test:*), Bash(pytest:*), Read
---

Verify the working tree.

1. Run `make check` (format check, ruff incl. `S`, mypy strict, pytest, build).
2. If anything fails, report the failing command and the relevant output, then propose the
   smallest fix. Do not mutate files here; apply fixes deliberately (`make format`), re-verify.
3. On success, give a one-line green summary with the exact commands run.

A completion claim without this gate executed is a defect (`AGENTS.md` section 5).
