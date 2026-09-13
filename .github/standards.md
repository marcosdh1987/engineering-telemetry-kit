# Standards

Binding conventions for code, tests, and verification. `AGENTS.md` holds the boundaries and
the working loop; this page holds the mechanics.

## Tooling

- Python >= 3.11, `uv` for environments, `make` for every gate. Never `pip install` ad hoc.
- `make install-dev` · `make format` (ruff format + safe fixes, local only) · `make lint`
  (format check + ruff incl. `S` security rules) · `make typecheck` (mypy strict) ·
  `make test` (pytest) · `make package` (build) · `make check` (all of the above; CI runs this).
- CI is read-only: it verifies, never formats or fixes. Fix locally, then re-run `make check`.
- Tool versions are pinned in `pyproject.toml` (`ruff>=0.16,<0.17`) and `.pre-commit-config.yaml`
  so formatter output is deterministic across machines and CI.

## Code style

- `from __future__ import annotations`; absolute imports (`from engobs.x import y`); ruff line
  length 100; `X | None` unions; `StrEnum` for closed vocabularies.
- Typed everywhere: mypy `strict` passes on `src/`. Prefer small frozen dataclasses for results
  and pydantic models (`extra="forbid"`) for anything parsed from files, env, or the network.
- Logging: module logger `logging.getLogger("engobs")`; log status codes, event types, and
  error class names — never payloads, headers, keys, or salts.
- Errors in the telemetry path are caught, logged, and turned into a result object. Only
  configuration misuse (e.g. strict mode without a salt) may surface as a non-zero exit.
- Security rules (`ruff S`) are on. Justified exceptions live in `pyproject.toml`
  `per-file-ignores` with a one-line reason; do not add blanket `# noqa`.

## Test conventions

- `pytest`, plain functions, `tmp_path` + `monkeypatch`. No network: mock HTTP by
  `monkeypatch.setattr(http_transport.request, "urlopen", fake)`; urllib capitalizes header
  keys (`User-agent`), so compare lower-cased.
- Git behavior is tested against a throwaway repo created with `subprocess` (`git init -b main`,
  a commit, an `origin` remote) — see `tests/test_cli.py`.
- Security tests (`tests/test_security.py`) assert that forbidden fields never appear in
  payloads and secrets never appear in logs. Extend them when you touch events or transport.
- Tests verify behavior, not mocks: assert on the request that was built or the result
  returned, not on call counts.

## Retry and malformed-command policy

- Run each verification command once per hypothesis. If it fails, diagnose before re-running.
- Never re-run the same failed command or re-apply the same failed patch more than twice.
- A truncated or malformed command is never retried as-is; rewrite it deliberately.
- Fallback order when a runner is missing: `make <target>` -> `.venv/bin/pytest <target>` ->
  direct execution of the real test function. Never a self-written approximation.

## Workflow failure signals (stop and re-ground)

- A "done" or "should work" claim without an executed command and its result.
- Editing a file you have not read in this session.
- Three edits to the same file without a new diagnosis.
- Re-reading unchanged governance or code without updating the plan.
- Changing files outside the stated scope without saying so first.

## Validation checklist (before handing over)

1. Focused test for the changed behavior ran and passed; `make check` is green; output pasted.
2. Boundaries in `AGENTS.md` section 2 untouched (or an ADR explains the change).
3. Behavior change -> tests added/updated and `docs/` updated.
4. Non-obvious learning -> `memory/learnings.md`; hard-to-reverse decision -> `docs/adr/`.
5. Nothing staged or committed; changed files listed in the handoff.
