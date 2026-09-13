# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Marcos Soto (maintainer)
- **Related:** `docs/adr/README.md`, `AGENTS.md` section 7

## Context

`engobs` is developed largely with AI coding agents. Decisions made in one session (why the
transport is stdlib-only, why the schema is closed) were only recoverable by reading code or
asking the maintainer, so agents re-litigated them or violated them by accident.

## Decision

We will record hard-to-reverse decisions as numbered ADRs under `docs/adr/`, using
`0000-template.md`, and list them in `docs/adr/README.md`. Existing foundational decisions are
recorded retroactively (ADR-0002, ADR-0003) so the index is useful from day one.

## Consequences

- Agents and contributors can cite an ADR instead of re-deriving rationale.
- Slightly more ceremony for schema, dependency, privacy, transport, and config changes.
- Routine changes stay ADR-free; durable but small facts go to `memory/learnings.md`.

## Alternatives considered

- **Rationale in commit messages only** — not discoverable, not loaded into agent context.
- **A single DECISIONS.md** — grows unbounded and loses the supersede/immutability semantics.
