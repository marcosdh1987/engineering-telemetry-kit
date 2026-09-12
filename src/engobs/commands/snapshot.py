from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engobs.commands.common import configure_logging, load_runtime_config, strict_mode_ready
from engobs.domain.events import EventType, TelemetryEvent
from engobs.git.context import GitSnapshot, get_snapshot
from engobs.privacy.policy import StrictPrivacyError, apply_privacy_mode
from engobs.state.store import should_emit_heartbeat, update_snapshot_fingerprint
from engobs.transport.http import send_event


def _base_event(
    snapshot: GitSnapshot,
    config_organization: str | None,
    config_project: str | None,
    config_repository: str | None,
) -> dict[str, Any]:
    repository = config_repository or snapshot.repository
    return {
        "organization": config_organization or snapshot.organization,
        "project": config_project or snapshot.project,
        "repository": repository,
        "branch": snapshot.branch,
        "work_unit_id": f"{repository or 'repo'}:{snapshot.branch}",
        "git_head_sha": snapshot.git_head_sha,
        "git_base_sha": snapshot.git_base_sha,
        "commits_count": snapshot.commits_count,
        "new_commits": snapshot.new_commits,
        "files_changed_count": snapshot.files_changed_count,
        "lines_added": snapshot.lines_added,
        "lines_deleted": snapshot.lines_deleted,
        "dirty_files_count": snapshot.dirty_files_count,
        "untracked_files_count": snapshot.untracked_files_count,
        "dirty_lines_added": snapshot.dirty_lines_added,
        "dirty_lines_deleted": snapshot.dirty_lines_deleted,
        "is_trunk": snapshot.is_trunk,
    }


def run_snapshot(cwd: Path, *, profile: str | None, trigger: str, force: bool) -> int:
    snapshot = get_snapshot(cwd)
    config, repo_root = load_runtime_config(cwd, profile)
    configure_logging(config.debug)

    branch_payload = _base_event(snapshot, config.organization, config.project, config.repository)
    branch_payload.update(
        {
            "event_type": EventType.BRANCH_SNAPSHOT,
            "trigger": trigger,
            "activity_window": f"{config.heartbeat_seconds}s",
            "in_progress_activity": (
                snapshot.dirty_files_count + snapshot.untracked_files_count
            )
            > 0,
        }
    )
    branch_event = TelemetryEvent.model_validate(branch_payload).finalized(bucket_seconds=60)

    events_to_send = [branch_event]
    occurred_at = datetime.now(UTC)
    heartbeat_key = f"{snapshot.repository or 'repo'}:{snapshot.branch}:activity"
    has_in_progress_work = (snapshot.dirty_files_count + snapshot.untracked_files_count) > 0
    if force or has_in_progress_work:
        should_send_activity = force or should_emit_heartbeat(
            repo_root,
            heartbeat_key,
            int(occurred_at.timestamp()),
            config.heartbeat_seconds,
        )
        if should_send_activity:
            activity_payload = _base_event(
                snapshot,
                config.organization,
                config.project,
                config.repository,
            )
            activity_payload.update(
                {
                    "event_type": EventType.ACTIVITY_OBSERVED,
                    "trigger": trigger,
                    "activity_window": f"{config.heartbeat_seconds}s",
                    "in_progress_activity": True,
                }
            )
            activity_event = TelemetryEvent.model_validate(activity_payload).finalized(
                bucket_seconds=config.heartbeat_seconds
            )
            events_to_send.append(activity_event)

    for event in events_to_send:
        try:
            if strict_mode_ready(config):
                event = apply_privacy_mode(event, config).finalized(bucket_seconds=60)
            else:
                print("WARN strict privacy mode is not ready; skipping telemetry send")
                continue
        except StrictPrivacyError as exc:
            print(f"WARN {exc}")
            continue
        result = send_event(config, event)
        if not result.ok:
            print(f"WARN telemetry not sent: {result.message}")
            continue
        if event.event_type == EventType.BRANCH_SNAPSHOT:
            update_snapshot_fingerprint(
                repo_root,
                event.event_id or "",
                event.occurred_at.isoformat(),
            )
    return 0
