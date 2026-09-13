# Current context

> Living snapshot of where the project is. Keep it short; move stale items to `learnings.md`
> or delete them.

## Project

`engobs`: privacy-first Engineering Delivery telemetry CLI (schema v4). This repo owns "how to
instrument a repository"; the `ai-gateway` repo owns the backend/control plane.

## Active focus

- 0.1.1 (2026-09-12): explicit client identity (`User-Agent: engobs/<version>`), doctor HINTs
  and configuration-source visibility, valid Claude Code hooks (stdin session id), and the
  wire adapter that makes events acceptable to the collector (ADR-0005). Validated end to end
  against `https://telemetry.msinnovatech.com.ar` (Cloudflare): snapshot, activity,
  verification and AI-session events accepted with 202. Pending: maintainer commit + push,
  then `uv tool install --force git+ssh://...` on instrumented workstations and
  `engobs install` once more per repo (migrates Claude hook entries).
- Next candidates: dashboard validation in the gateway (project/branch/LOC/verification/AI
  session rows), and deciding whether to replace the flat internal `TelemetryEvent` with the
  wire model (see ADR-0005 consequences).

## Constraints and decisions in force

- Privacy-first closed schema (ADR-0002); stdlib-only non-blocking transport (ADR-0003);
  Harness Lite scope (ADR-0004); collector wire contract via adapter (ADR-0005). Maintainer commits; agents never run `git commit`.

## Open threads

- `engobs snapshot` on trunk emits `activity_observed` alongside the snapshot with
  `--force`; confirm the gateway's activity views treat manual snapshots as intended.
- The flat internal model still carries fields the wire drops (`activity_window="300s"`,
  `verification_status`, `work_unit_id="repo:branch"`); harmless but redundant.
- `WARN auth: ENGOBS_API_KEY not configured` is expected while the backend runs with
  `auth_required=false`; revisit wording if pilots find it noisy.
