# ADR-0005: Emit the collector's schema v4 wire contract through a wire adapter

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Marcos Soto (maintainer)
- **Related:** ADR-0002, ADR-0003, `src/engobs/domain/wire.py`, `tests/test_wire.py`,
  `ai-gateway` `src/ai_gateway/engineering/contract.py`, `memory/learnings.md`

## Context

Once the Cloudflare block was lifted (explicit User-Agent), every `engobs` request reached the
collector and was rejected with `422 invalid_payload`. The collector's schema v4 is a closed
**envelope + typed `attributes`** contract mirrored from the `ml-langchain-agent` emitter:
`work_unit_id` is a UUID5 in a shared namespace, `in_progress_activity` is an object, AI
sessions are a separate `AiObservation` family (`observation_type`, `tool`, `session_id`),
and Postgres stores `event_id` as a UUID. `engobs` had reimplemented schema v4 as a flat
event with `work_unit_id = "repo:branch"` and a SHA-256 `event_id`, so it had never been
wire-compatible; the 403 had masked it.

## Decision

We will keep engobs' flat, privacy-validated `TelemetryEvent` as the internal model and add a
single **wire adapter** (`domain/wire.py`, applied inside `send_event`) that renders the
collector contract:

- envelope (`event_id` as a deterministic UUID5 of engobs' fingerprint, `schema_version`,
  `telemetry_scope`, `occurred_at`, organization/project/repository/branch, `work_unit_id`);
- `DevelopmentEvent` with nested `attributes` (trigger, git counts, `in_progress_activity`,
  verification `attempt`/`duration_seconds`) for `POST /events`;
- `AiObservation` (`observation_type`, `tool`, `session_id`, `model`, `attributes`) for
  `POST /ai-observations`;
- `work_unit_id` derived with the shared namespace `5f7c2a2e-6c1a-4b58-9f2e-3a9d4b2c1e01`
  from the values *as sent* (pseudonymized in strict mode), windowed by UTC day on trunk;
- the forbidden-field validator runs again on the wire payload;
- `WireContractError` (missing organization/project/repository) is a non-blocking WARN, and
  `engobs doctor` reports incomplete identity as `ERROR` with a hint.

The backend is the source of truth for the contract; `tests/test_wire.py` carries a mirror
of its accepted keys and must be updated together with the collector.

## Consequences

- Events, activity, verification and AI observations are accepted (202) by the real gateway.
- Commands, privacy modes, fingerprints and existing tests are unchanged; only the last step
  before the POST knows the wire shape.
- Two schemas exist in the client (flat internal, nested wire). Acceptable for now; a future
  ADR may replace the flat model with the wire model directly.
- Any contract change on the collector requires updating `wire.py` and the mirror in
  `tests/test_wire.py`.

## Alternatives considered

- **Relax the collector to accept flat events** — breaks the other emitter and moves the
  trust boundary; the backend is deliberately closed.
- **Replace `TelemetryEvent` with the nested contract everywhere** — larger, riskier change
  touching every command and privacy path; deferred.
