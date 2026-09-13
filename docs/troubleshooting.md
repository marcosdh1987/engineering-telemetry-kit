# Troubleshooting

Real problems found while onboarding repositories behind reverse proxies and CDNs. Start
with `engobs doctor`: every failed probe prints `HINT` lines that map to a section here.

## 403 from engobs, but curl works

Symptom:

```text
WARN endpoint_reachable: HTTP 403 Forbidden
HINT a reverse proxy/CDN may be blocking the engobs client
HINT Cloudflare rejected the HTTP client signature. Verify the engobs User-Agent (upgrade engobs) or the Cloudflare security rules.
```

Reproduce from a shell:

```bash
curl -i https://telemetry.example.com/health
curl -i -A "Python-urllib/3.11" https://telemetry.example.com/health
```

If the first succeeds and the second returns `403` with `error code: 1010` and
`server: cloudflare`, the CDN's browser-integrity check is rejecting the generic Python
User-Agent. engobs < 0.1.1 sent exactly that signature. Fix: upgrade engobs
(`uv tool install --force ...`); since 0.1.1 every request identifies itself as
`engobs/<version>`. If a newer engobs is still blocked, allow-list the `engobs/` User-Agent
(or the collector path) in the Cloudflare/WAF rules.

## 422 from `POST /events` with an empty payload

```bash
curl -i -X POST https://telemetry.example.com/events \
  -H "Content-Type: application/json" -d '{}'
```

`422 invalid_payload` is a **good** sign: the request traversed the proxy and reached the
collector, which rejected an intentionally invalid body. Only `403`, `404`, `502`-`504` or a
timeout indicate an infrastructure problem.

## 422 invalid_payload from engobs itself

engobs < 0.1.1 sent a flat event the collector does not accept; upgrade. On a current engobs,
run with `ENGOBS_DEBUG=true` to see the collector's response
(`telemetry http error detail={"error":"invalid_payload","detail":[...]}`) — it names the
rejected field. A mismatch usually means the collector's contract changed; update
`src/engobs/domain/wire.py` and its mirror in `tests/test_wire.py` (ADR-0005).

## 503 storage_error

The request passed validation and the collector failed to persist it. `/health` reporting
`"database": true` only proves connectivity. Check the collector logs (`storage error while
ingesting ...`). Known cause with engobs < 0.1.1: a non-UUID `event_id` rejected by Postgres.

## 401 Unauthorized

```text
ERROR auth: endpoint rejected credentials
HINT endpoint rejected credentials: set ENGOBS_API_KEY (or a profile api_key)
```

The backend requires telemetry auth. Export `ENGOBS_API_KEY` (never in `.engobs.toml`).
Confirm you are using the telemetry gateway key, not a LiteLLM virtual key.

## 404 on /health

The `endpoint` must be the gateway base URL (`https://telemetry.example.com`), not a path
such as `.../events`. Also check the reverse proxy forwards `/health`, `/events` and
`/ai-observations` to the collector.

## Connection failed / TLS errors

```text
WARN endpoint_reachable: URLError: ...
HINT connection failed: check network, DNS, proxy, and TLS (ENGOBS_CA_BUNDLE)
```

Corporate HTTPS with a private CA: set `ENGOBS_CA_BUNDLE=/path/to/company-ca.pem` (or
`ca_bundle` in the config). `ENGOBS_VERIFY_TLS=false` works but is reported as a warning by
`engobs doctor` and should not be used beyond a short experiment.

## Reverse proxy setup (Nginx Proxy Manager or similar)

Recommended topology: expose only an HTTPS hostname; keep the collector on an internal
network and forward to it over HTTP.

```text
https://telemetry.example.com      (public, TLS terminated at the proxy / CDN)
        |
        v
http://<collector-host>:<collector-port>   (internal only, not reachable from the Internet)
```

Checklist:

- Forward `/health`, `/events`, `/ai-observations` unchanged (no path rewrite).
- Do not require browser cookies, JS challenges, or "Under Attack" mode on this hostname;
  if the CDN applies browser-integrity checks, allow the `engobs/` User-Agent.
- Do not publish the collector port directly; only the proxy should reach it.
- Default request body limits are fine: events are a few KB of JSON.

## Doctor says the global config is missing

```text
INFO global_config: not configured (optional)
```

This is informational. Repo-level `.engobs.toml`, a global profile, or environment variables
are all valid configuration sources; `OK configuration_source: ...` shows which ones apply.
A `WARN profile: profile 'x' selected but not defined` means a profile name is referenced
that no config file defines.

## Claude Code hooks do not emit AI sessions

Repositories instrumented with engobs < 0.1.1 have hook entries in `.claude/settings.json`
that Claude Code ignores (invalid shape). Run `engobs install` again to migrate them, then
restart Claude Code. `engobs doctor` reports `OK claude_hooks: installed` once the managed
groups are present.

## Old engobs still in use after upgrading

`which engobs` should point at the `uv tool` shim. Git and Claude hooks call `engobs` from
`PATH`, so the upgraded binary is used automatically; no hook reinstall is needed.
