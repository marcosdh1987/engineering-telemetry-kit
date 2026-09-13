# Development guide

How to work on `engobs` itself, with or without an AI coding agent. Agents read `AGENTS.md`
automatically; this page is the human entry point and links the pieces together.

## Local setup

```bash
uv venv .venv && uv pip install -e ".[dev]"
source .venv/bin/activate
make check
```

`make check` is the only gate and CI runs exactly it:

| Step | Command | Catches |
| --- | --- | --- |
| format | `ruff format --check src tests` | formatting drift (ruff pinned to 0.16.x) |
| lint | `ruff check src tests` | style, imports, bugbear, pyupgrade, security (`S`) |
| types | `mypy src` (strict) | typing errors in the package |
| tests | `pytest` | behavior, privacy and security regressions, harness drift |
| package | `python -m build` | packaging errors |

`make format` applies formatting and safe fixes locally; CI never mutates the tree.

## Harness Lite

The repo ships a small governance layer so any agent (Claude Code, Codex, OpenCode, Copilot)
behaves consistently. Principle: *small context, strong boundaries, automatic verification,
durable learning* (ADR-0004).

| Piece | Path | Purpose |
| --- | --- | --- |
| Canonical instructions | `AGENTS.md` (imported by `CLAUDE.md`) | product summary, inviolable privacy/security boundaries, repo map, working loop, gate, debugging protocol, ADR/memory rules |
| Structure | `.github/architecture.md` | data flow, dependency direction, extension points |
| Mechanics | `.github/standards.md` | tooling, style, test conventions, retry policy, validation checklist |
| Decisions | `docs/adr/` | ADRs; write one for hard-to-reverse changes (`docs/adr/README.md`) |
| Memory | `memory/context.md`, `memory/learnings.md` | current focus and non-obvious facts; read at start, append at end |
| Claude Code | `.claude/settings.json`, `.claude/hooks/`, `.claude/commands/` | non-blocking nudges, permission prompts on git mutations, `/plan` `/verify` `/retro` `/adr` |
| Self-check | `tests/test_harness.py` | fails when governance files, the ADR index, or hook scripts drift |

Working loop: **Ground** (read `AGENTS.md`, memory, the code) -> **Plan** (1-3 sentences
before editing) -> **Verify** (focused test, then `make check`) -> **Compound** (memory entry
or ADR, docs update). A completion claim without an executed verification command is a defect.

## Common changes

- **New command:** `src/engobs/cli.py` + `src/engobs/commands/<name>.py`, test in
  `tests/test_cli.py`, mention in `README.md`.
- **New event field:** ADR first; `src/engobs/domain/events.py`; review `FORBIDDEN_KEYS` and
  `STRICT_FIELDS`; update `docs/privacy.md`; coordinate `SCHEMA_VERSION` with the backend.
- **New config key:** `src/engobs/config/models.py` (both models) + `ENV_MAP` in `loader.py`;
  test precedence in `tests/test_config.py`; document in `docs/enterprise-deployment.md`.
- **Transport/header change:** single header builder in `src/engobs/transport/http.py`;
  assert headers in `tests/test_transport.py`; never log secrets.

## Git policy

Agents never commit, push, merge, or rebase; they leave changes unstaged and the maintainer
commits. Pull requests use `.github/PULL_REQUEST_TEMPLATE.md`: paste what you ran.
