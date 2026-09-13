# ADR-0002: Privacy-first closed telemetry schema

- **Status:** Accepted (records an existing decision)
- **Date:** 2026-09-12
- **Deciders:** Marcos Soto (maintainer)
- **Related:** `docs/privacy.md`, `SECURITY.md`, `src/engobs/domain/events.py`,
  `src/engobs/privacy/`, `AGENTS.md` section 2

## Context

The kit is installed in client repositories and on developer workstations. Adoption depends on
a credible guarantee that it measures the engineering *process* (commits, branches, aggregate
LOC, verification outcomes, AI session presence) and never the *content* (code, diffs, prompts)
or the *person* (name, email). A telemetry client that could leak either would be rejected by
security reviews and by developers.

## Decision

We will keep the telemetry schema closed and validated client-side:

- `TelemetryEvent` is a pydantic model with `extra="forbid"`; only enumerated aggregate fields exist.
- `privacy/validation.py` maintains `FORBIDDEN_KEYS` (content, identity, secrets, paths, output)
  and every event is checked recursively before privacy transformation and again after.
- `strict` mode pseudonymizes `STRICT_FIELDS` (organization, project, repository, branch, work
  unit, commit SHAs, session id) with a local salt that is never transmitted or logged.
- Adding an event field requires an ADR plus a `FORBIDDEN_KEYS` / `STRICT_FIELDS` review;
  `SCHEMA_VERSION` changes are coordinated with the backend.

## Consequences

- Privacy guarantees are enforced by code and tests (`tests/test_security.py`,
  `tests/test_privacy.py`), not by policy documents alone.
- The schema evolves slowly and deliberately; ad-hoc fields are impossible by construction.
- Backend-side redaction is unnecessary; the client is the trust boundary.

## Alternatives considered

- **Open schema with server-side redaction** — moves the trust boundary to infrastructure the
  developer cannot inspect; a misconfigured backend would leak content.
- **Allow-list only, no forbidden-key check** — an allow-listed field named `diff` would still
  pass; the double check catches naming mistakes and nested payloads.
