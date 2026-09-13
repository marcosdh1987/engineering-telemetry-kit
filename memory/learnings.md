# Learnings

Append new entries at the top. One fact per entry; see `README.md` for the format.

## engobs' flat event was never the collector's schema v4 — 2026-09-12

The Cloudflare 403 masked a second failure: with the client identity fixed, every POST got
`422 invalid_payload`. The collector (`ai-gateway` `engineering/contract.py`) expects an
envelope + typed `attributes`, UUID5 `work_unit_id` in namespace
`5f7c2a2e-6c1a-4b58-9f2e-3a9d4b2c1e01`, a separate `AiObservation` family, and stores
`event_id` as a Postgres UUID (a SHA-256 hex `event_id` yields `503 storage_error`, not 422).

**Why it matters:** "schema v4" in both repos meant different shapes; `/health` and a 422 on
`POST {}` do not prove the real payload is accepted.
**How to apply:** the wire shape lives only in `src/engobs/domain/wire.py` (ADR-0005), mirrored
in `tests/test_wire.py`. When the collector contract changes, update both. Validate end to end
with `ENGOBS_DEBUG=true engobs snapshot --trigger manual --force` and expect `status=202`.

## `uv tool install --force .` can reuse a stale cached wheel — 2026-09-12

Reinstalling from the local checkout with the same version number reused a cached 0.1.1 wheel
that predated new modules, so the CLI kept the old behavior while tests were green.

**Why it matters:** "reinstalled and still broken" was a cache artifact, not a code bug.
**How to apply:** for local validation use
`uv tool install --force --reinstall --no-cache .`; confirm with
`ls ~/.local/share/uv/tools/engineering-telemetry-kit/lib/python*/site-packages/engobs/`.

## Claude Code hooks: session id arrives on stdin, entries need `hooks[]` — 2026-09-12

Claude Code delivers `{"session_id", "hook_event_name", "cwd", ...}` as JSON on the hook's
stdin; there is no `CLAUDE_SESSION_ID` environment variable. Each `hooks.<Event>` item must be
`{"matcher"?, "hooks": [{"type": "command", "command": ...}]}`; the `{"id", "command",
"managed_by"}` entries engobs < 0.1.1 wrote were silently ignored.

**Why it matters:** AI sessions never reached the backend on instrumented repos.
**How to apply:** `engobs ai-session` reads the session id from stdin when `--session-id` is
omitted; `engobs install` migrates legacy entries. Restart Claude Code after installing.

## Cloudflare error 1010 rejects urllib's default User-Agent — 2026-09-12

Pointing `engobs doctor`/`snapshot` at a gateway behind Cloudflare returned `403 Forbidden`
while `curl /health` returned 200 and `curl -X POST /events -d '{}'` returned
`422 invalid_payload`. Reproducing with `curl -A "Python-urllib/3.11"` returned 403 with body
`error code: 1010`: Cloudflare's browser-integrity check blocks the generic urllib signature.

**Why it matters:** the backend and the proxy path were healthy; the only broken piece was
the client identity. A 422 on an empty POST is a *good* sign (the request reached the
collector's schema validation).
**How to apply:** the transport must send an explicit `User-Agent: engobs/<version>` on every
request (ADR-0003 consequence). When diagnosing 403s, compare `curl` with and without
`-A "Python-urllib/3.x"` before touching auth or TLS.

## `make check` did not enforce formatting; ruff versions format differently — 2026-09-12

Before 2026-09-12 the Makefile ran `ruff check` but not `ruff format --check`, so three files
drifted. ruff 0.6.x and 0.16.x also disagree on implicit string concatenation and `UP038`,
so pre-commit (pinned) and CI (`ruff>=0.6` -> latest) could pass or fail differently.

**Why it matters:** "CI is green" was not the same statement on every machine.
**How to apply:** keep `ruff>=0.16,<0.17` in `pyproject.toml` and the matching `rev` in
`.pre-commit-config.yaml`; bump both together. `make lint` now runs the format check.

## Tests mock urllib at the module attribute; header keys are capitalized — 2026-09-12

HTTP tests replace `engobs.transport.http.request.urlopen` via `monkeypatch.setattr` and
inspect `req.header_items()`. urllib's `Request.add_header` capitalizes keys
(`User-agent`, `Content-type`), and the default `Python-urllib` User-Agent is only added by
the opener at open time, so it never shows up in a mocked request.

**Why it matters:** header assertions that compare exact case, or that expect the default UA,
fail for the wrong reason.
**How to apply:** compare `{k.lower(): v for k, v in req.header_items()}`; assert only on
headers the code sets explicitly.

## `engobs install` in this repo edits the tracked `.claude/settings.json` — 2026-09-12

The repo now ships `.claude/settings.json` (governance hooks + git permission prompts).
Running `engobs install` here (dogfooding) appends engobs-managed entries to that same file.

**Why it matters:** the diff looks like a governance change but is a local instrumentation
side effect.
**How to apply:** do not commit the engobs-managed entries; `git checkout .claude/settings.json`
or `engobs uninstall` before handing over.

<!-- Add new learnings above this line -->
