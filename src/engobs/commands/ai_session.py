from __future__ import annotations

from pathlib import Path

from engobs.commands.common import configure_logging, load_runtime_config, strict_mode_ready
from engobs.domain.events import EventType, TelemetryEvent
from engobs.git.context import get_snapshot
from engobs.privacy.policy import StrictPrivacyError, apply_privacy_mode
from engobs.privacy.pseudonymize import opaque_session_id
from engobs.state.store import set_ai_session_state
from engobs.transport.http import send_event


def run_ai_session(
    cwd: Path,
    *,
    profile: str | None,
    action: str,
    tool: str,
    session_id: str,
    model: str | None,
) -> int:
    snapshot = get_snapshot(cwd)
    config, repo_root = load_runtime_config(cwd, profile)
    configure_logging(config.debug)
    event_type = EventType.AI_SESSION_STARTED if action == "start" else EventType.AI_SESSION_ENDED
    event = TelemetryEvent(
        event_type=event_type,
        organization=config.organization or snapshot.organization,
        project=config.project or snapshot.project,
        repository=config.repository or snapshot.repository,
        branch=snapshot.branch,
        git_head_sha=snapshot.git_head_sha,
        git_base_sha=snapshot.git_base_sha,
        ai_tool=tool,
        model=model,
        opaque_session_id=opaque_session_id(session_id),
        trigger="ai_turn",
    ).finalized()
    try:
        if strict_mode_ready(config):
            event = apply_privacy_mode(event, config).finalized(bucket_seconds=60)
        else:
            print("WARN strict privacy mode is not ready; skipping telemetry send")
            return 0
    except StrictPrivacyError as exc:
        print(f"WARN {exc}")
        return 0
    result = send_event(config, event)
    if not result.ok:
        print(f"WARN telemetry not sent: {result.message}")
        return 0
    set_ai_session_state(repo_root, tool, session_id, action == "start")
    return 0
