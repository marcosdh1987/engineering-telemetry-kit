# ADR-0003: Standard-library-only, non-blocking HTTP transport

- **Status:** Accepted (records an existing decision)
- **Date:** 2026-09-12
- **Deciders:** Marcos Soto (maintainer)
- **Related:** `src/engobs/transport/http.py`, `docs/integrations/git-hooks.md`,
  `memory/learnings.md` (Cloudflare 1010 entry), `AGENTS.md` section 2

## Context

`engobs` runs inside Git hooks and AI-tool hooks on arbitrary developer machines. It must
install anywhere (`uv tool install`), start fast, and never block a commit, checkout, or AI
turn — even when the gateway is down or behind restrictive corporate HTTP infrastructure.

## Decision

We will implement transport with `urllib` from the standard library and keep `pydantic` as the
only runtime dependency. Delivery is best-effort: short timeout (1.5 s default), every transport
error is logged and converted into a `DeliveryResult`/`HealthResult`, hooks invoke `engobs` with
`|| true`, and nothing is retried or queued. TLS verification is on by default with an optional
CA bundle; disabling it is allowed but surfaced loudly by `engobs doctor`.

## Consequences

- Zero-friction installs and no dependency-resolution conflicts inside client repos.
- Everything `requests`/`httpx` would do for us must be explicit: **client identity
  (`User-Agent`), `Accept`, JSON content type, and header centralization are our responsibility.**
  urllib's default `Python-urllib/x.y` User-Agent is rejected by Cloudflare's browser-integrity
  check (error 1010); the client must send its own identity (see memory entry 2026-09-12).
- Events emitted while the gateway is unreachable are lost by design; the backend must
  tolerate gaps, and heartbeat/snapshot triggers provide eventual coverage.
- Adding a runtime dependency to the transport requires superseding this ADR.

## Alternatives considered

- **`requests`/`httpx`** — nicer API and sane default headers, but a dependency tree inside
  every instrumented repo and slower cold start in hooks.
- **Local queue with retry** — better delivery guarantees, but persistent local state, more
  code paths that could leak, and hooks that can stall on disk contention.
