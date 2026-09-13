# Architecture Decision Records

An ADR captures one significant decision: the context that forced a choice, the choice, and
its consequences. ADRs are immutable once accepted; a changed decision gets a new ADR that
supersedes the old one.

## When to write one

Write an ADR when a decision is **hard to reverse** or would otherwise have to be
reverse-engineered by the next contributor (human or agent):

- adding or replacing a runtime dependency
- adding, removing, or renaming an event field, or bumping `SCHEMA_VERSION`
- changing a privacy or transport boundary (what is sent, how, to whom)
- changing configuration semantics (precedence, new source, new secret handling)
- a convention everyone must follow

Skip an ADR for routine, easily reversible changes; that is what `memory/learnings.md` and
commit messages are for.

## How to write one

1. Copy `0000-template.md` to `NNNN-short-kebab-title.md` (next number, zero-padded).
2. Fill in Context, Decision, Consequences, Alternatives considered. One page is plenty.
3. Status `Proposed` until agreed, then `Accepted`; `Superseded by ADR-XXXX` when replaced.
4. Add it to the index below. In Claude Code, `/adr <title>` scaffolds steps 1-4.

## Index

- [0001 — Record architecture decisions](0001-record-architecture-decisions.md)
- [0002 — Privacy-first closed telemetry schema](0002-privacy-first-closed-telemetry-schema.md)
- [0003 — Standard-library-only, non-blocking HTTP transport](0003-stdlib-only-non-blocking-transport.md)
- [0004 — Adopt a Harness Lite for agent-assisted development](0004-adopt-harness-lite.md)
