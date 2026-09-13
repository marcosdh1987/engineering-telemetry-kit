# Changelog

All notable changes to `engineering-telemetry-kit` (the `engobs` CLI).

## 0.1.1 — 2026-09-12

Operational fixes found during the first real onboarding behind Cloudflare.

### Fixed

- **Events are now accepted by the Engineering Gateway.** engobs sent a flat event; the
  collector's schema v4 is an envelope with typed `attributes`, UUID5 `work_unit_id`,
  `AiObservation` for sessions and a UUID `event_id`. A wire adapter (`domain/wire.py`,
  ADR-0005) renders that contract; previously every POST was rejected with `422` (or `503
  storage_error` for the non-UUID `event_id`) once it got past the CDN.
- Every request now sends an explicit client identity: `User-Agent: engobs/<version>`,
  `Accept: application/json`, and `Content-Type: application/json` on POSTs. urllib's default
  `Python-urllib/x.y` User-Agent was rejected by Cloudflare's browser-integrity check
  (`403`, `error code: 1010`), which made `engobs doctor` and `engobs snapshot` fail behind
  the CDN while `curl` worked.
- Claude Code hooks written by `engobs install` now use the documented hooks schema
  (`{"matcher", "hooks": [{"type": "command", ...}]}`) and read the session id from the JSON
  Claude Code pipes on stdin. Previous entries never fired; they are migrated on the next
  `engobs install` (and removed by `engobs uninstall`).

### Changed

- `engobs doctor` reports `HTTP <code> <reason>` and prints `HINT` lines for common failures
  (401, 403, 404, 5xx, connection errors) plus a Cloudflare-specific hint when the response
  carries `server: cloudflare` or `error code: 1010`.
- `engobs doctor` shows the configuration source (`repo=.engobs.toml`, `global=...`,
  `env=...`, `profile=...`). A missing global or repo config file is now `INFO` (optional)
  instead of `WARN`; a selected profile that no file defines is a `WARN`.
- `HealthResult` carries the `Server` header and a body snippet (max 512 bytes) of failed
  probes; `send_event` logs `server=<name>` on HTTP errors. Never payloads or headers.
- `--session-id` is optional for `engobs ai-session`; it defaults to the hook stdin JSON.
- `engobs doctor` reports incomplete organization/project/repository as `ERROR` with a hint
  (the collector requires all three).
- With `ENGOBS_DEBUG=true`, HTTP error responses from the gateway are logged (`detail=...`);
  payloads and headers are never logged.
- Version is single-sourced from `src/engobs/__init__.py` (hatch dynamic version).

### Added

- `docs/onboarding.md` (instrument an existing repository, the validated flow) and
  `docs/troubleshooting.md` (reverse proxy / CDN / auth issues).
- Regression test for the Cloudflare 1010 block and header-identity tests for
  `/health`, `/events`, `/ai-observations`; wire-contract tests mirroring the collector.

## 0.1.0 — 2026-09

Initial release: Git hooks, Claude Code hooks, verification wrapper, schema v4 events,
privacy modes, profiles.
