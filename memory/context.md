# Current context

> Living snapshot of where the project is. Keep it short; move stale items to `learnings.md`
> or delete them.

## Project

`engobs`: privacy-first Engineering Delivery telemetry CLI (schema v4). This repo owns "how to
instrument a repository"; the `ai-gateway` repo owns the backend/control plane.

## Active focus

- Harness Lite landed (2026-09-12): `AGENTS.md` + `CLAUDE.md`, `.github/architecture.md`,
  `.github/standards.md`, `memory/`, `docs/adr/0001-0004`, `.claude/` hooks and commands,
  stricter `make check` (format check + ruff `S`, ruff pinned to 0.16.x). See ADR-0004.
- Next: **User-Agent / Cloudflare fix + onboarding docs** (brief saved by the maintainer in the
  planning file for this work). Summary:
  - send `User-Agent: engobs/<version>` (fallback `engobs/dev`), `Accept: application/json`,
    JSON content type, `Authorization` only when configured; one header builder for
    `send_event` and `check_health`; redaction for logs.
  - `engobs doctor`: `HTTP 403 Forbidden` + `HINT` lines (reverse proxy/CDN; Cloudflare 1010
    when `server: cloudflare` or body `error code: 1010`); `HealthResult` gains server header
    and a <=512-byte body snippet; `send_event` logs `server=`.
  - missing global config must not be a WARN when repo config resolves; doctor shows the
    configuration source (repo/global/profile).
  - docs: `docs/onboarding.md`, `docs/troubleshooting.md`, README slimmed to a quickstart,
    `enterprise-deployment.md` repo-level vs global profile, LiteLLM key-alias correlation,
    auth pilot vs production, no secrets in `.engobs.toml`.
  - version 0.1.0 -> 0.1.1 (installed on workstations; distinguishable UA), `CHANGELOG.md`;
    regression test for Cloudflare 1010.

## Constraints and decisions in force

- Privacy-first closed schema (ADR-0002); stdlib-only non-blocking transport (ADR-0003);
  Harness Lite scope (ADR-0004). Maintainer commits; agents never run `git commit`.

## Open threads

- `src/engobs/ai/claude.py` writes hook entries shaped `{"id", "command", "managed_by"}`
  under `hooks.<Event>`. Claude Code's documented hooks schema is
  `[{"matcher": ..., "hooks": [{"type": "command", "command": ...}]}]`. Verify whether the
  managed entries actually fire; if not, fix in the User-Agent/onboarding work (affects
  onboarding step "AI tool").
- `engobs doctor` prints `WARN global_config: missing` even with a valid repo-only config
  (confusing; part of the next task).
- Version is duplicated in `pyproject.toml` and `src/engobs/__init__.py`; single-source it
  when bumping to 0.1.1.
