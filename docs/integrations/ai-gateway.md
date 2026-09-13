# AI Gateway integration

`engobs` is backend-agnostic. When pointed at an Engineering Gateway it uses:

| Call | Purpose |
| --- | --- |
| `GET {endpoint}/health` | `engobs doctor` reachability, auth and schema probe. Optional JSON body may advertise `supported_schema_versions`. |
| `POST {endpoint}/events` | Git snapshots, activity, verification events (schema v4 JSON). |
| `POST {endpoint}/ai-observations` | AI session start/end events. |

Every request carries the client identity, so reverse proxies and CDNs can allow-list it:

```text
User-Agent: engobs/<version>
Accept: application/json
Content-Type: application/json   (POST only)
Authorization: Bearer ******     (only when ENGOBS_API_KEY / api_key is configured)
```

## Wire format (schema v4)

The collector contract is closed (unknown keys are rejected). engobs renders it in
`src/engobs/domain/wire.py`; `tests/test_wire.py` mirrors the accepted keys.

```json
{
  "event_id": "<uuid>", "schema_version": 4, "telemetry_scope": "development",
  "occurred_at": "2026-09-12T23:30:00+00:00",
  "organization": "acme", "project": "payments", "repository": "payments-api",
  "branch": "feature/x", "work_unit_id": "<uuid5 of repository:branch>",
  "event_type": "branch_snapshot",
  "attributes": {
    "trigger": "commit", "is_trunk": false,
    "git_base_sha": "...", "git_head_sha": "...", "commits_count": 3, "new_commits": 1,
    "files_changed_count": 4, "lines_added": 50, "lines_deleted": 5,
    "in_progress_activity": {"dirty_files_count": 2, "untracked_files_count": 1,
                             "lines_added": 7, "lines_deleted": 0}
  }
}
```

AI sessions go to `/ai-observations` as `{"observation_type": "ai_session_started", "tool":
"claude", "session_id": "<opaque>", "model": ..., "attributes": {"is_trunk", "activity_window"}}`
with the same envelope. On trunk branches `activity_window` is the UTC day and
`work_unit_id` is derived from `repository:branch@<day>`. `organization`, `project` and
`repository` are required; `engobs doctor` reports `ERROR repository_identity` when they
cannot be resolved.

The kit never depends on a fixed hostname, organization, IP, or LiteLLM credential. How to run
the gateway (collector, storage, Metabase, LiteLLM, auth) is documented in the `ai-gateway`
repository; how to instrument a repository is documented here in `docs/onboarding.md`.
