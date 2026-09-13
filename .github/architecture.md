# Architecture

Read `AGENTS.md` first; this page adds the structural detail an agent needs before changing
module layout, data flow, or extension points.

## Data flow

```text
Git hooks (post-commit, post-checkout)   Claude hooks (SessionStart/Stop/SessionEnd)   engobs verify -- <cmd>
              |                                        |                                        |
              +----------------------------------------+----------------------------------------+
                                                       v
                                        engobs CLI  (src/engobs/cli.py)
                                                       v
                                  commands/  (install, doctor, snapshot, verify, ai_session)
                                                       v
                 config/loader.py  ->  ResolvedConfig          git/context.py  ->  GitSnapshot (aggregates only)
                                                       v
                          domain/events.py  ->  TelemetryEvent.finalized()  (forbidden-field validation #1)
                                                       v
                          privacy/policy.py  ->  apply_privacy_mode()        (strict pseudonymization)
                                                       v
                          privacy/validation.py                              (forbidden-field validation #2)
                                                       v
                          transport/http.py  ->  POST /events | /ai-observations, GET /health
                                                       v
                                        Engineering Gateway (any backend, configurable endpoint)
```

`state/store.py` keeps a tiny local state file (`.git/engobs/state.json`) for heartbeat
suppression and verification attempt counters. It never stores content.

## Dependency direction

- `domain/` and `privacy/` import nothing from `commands/`, `transport/`, `git/`, `ai/`.
- `transport/` knows only `ResolvedConfig` and `TelemetryEvent`; it must not inspect Git or files.
- `git/` and `ai/` know the filesystem and subprocess; they never build or send events.
- `commands/` orchestrate: load config, gather a snapshot, build an event, apply privacy, send.
- `cli.py` only parses arguments and dispatches.

Keep it this way. A privacy check that lives in `commands/` instead of `domain/`/`privacy/`
can be bypassed by the next command; a transport that reads Git state cannot be mocked.

## Extension points

| Change | Touch | Also |
| --- | --- | --- |
| New CLI command | `cli.py` (parser + dispatch), `commands/<name>.py` | `tests/test_cli.py`, `README.md` core commands, `docs/` |
| New event field | `domain/events.py` | ADR; review `privacy/validation.py` `FORBIDDEN_KEYS` and `privacy/policy.py` `STRICT_FIELDS`; coordinate `SCHEMA_VERSION` with the backend; `docs/privacy.md` table |
| New config key | `config/models.py` (both `ProfileConfig` and `ResolvedConfig`), `config/loader.py` `ENV_MAP` | `tests/test_config.py`, `docs/enterprise-deployment.md` |
| New HTTP endpoint or header | `transport/http.py` (single header builder) | `tests/test_transport.py` header assertions; never log secrets |
| New managed hook (Git or AI tool) | `git/hooks.py` or `ai/claude.py` | idempotent install, exact-block uninstall, `tests/test_hooks.py` |

## Decision policy

Choose the simplest solution compatible with the boundaries in `AGENTS.md`. Preserve existing
style and naming. Minimize file churn; no drive-by refactors. When two designs are equivalent,
prefer the one with fewer moving parts and no new dependency.
