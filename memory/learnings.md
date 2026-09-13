# Learnings

Append new entries at the top. One fact per entry; see `README.md` for the format.

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
