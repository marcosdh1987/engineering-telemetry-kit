from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from engobs.commands.common import configure_logging, load_runtime_config, strict_mode_ready
from engobs.config.models import ResolvedConfig
from engobs.domain.events import EventType, TelemetryEvent
from engobs.git.context import get_snapshot
from engobs.privacy.policy import StrictPrivacyError, apply_privacy_mode
from engobs.state.store import next_verification_attempt
from engobs.transport.http import send_event


def _emit(config: ResolvedConfig, event: TelemetryEvent) -> None:
    try:
        if strict_mode_ready(config):
            event = apply_privacy_mode(event, config).finalized(bucket_seconds=60)
        else:
            print("WARN strict privacy mode is not ready; skipping telemetry send")
            return
    except StrictPrivacyError as exc:
        print(f"WARN {exc}")
        return
    result = send_event(config, event)
    if not result.ok:
        print(f"WARN telemetry not sent: {result.message}")


def run_verify(cwd: Path, *, profile: str | None, command: list[str]) -> int:
    snapshot = get_snapshot(cwd)
    config, _ = load_runtime_config(cwd, profile)
    configure_logging(config.debug)
    attempt = next_verification_attempt(snapshot.repo_root)
    base: dict[str, Any] = {
        "organization": config.organization or snapshot.organization,
        "project": config.project or snapshot.project,
        "repository": config.repository or snapshot.repository,
        "branch": snapshot.branch,
        "git_head_sha": snapshot.git_head_sha,
        "git_base_sha": snapshot.git_base_sha,
        "verification_attempt": attempt,
    }
    started_payload = dict(base)
    started_payload.update(
        {
            "event_type": EventType.VERIFICATION_STARTED,
            "verification_status": "started",
        }
    )
    started_event = TelemetryEvent.model_validate(started_payload).finalized()
    _emit(config, started_event)

    start = time.perf_counter()
    completed = subprocess.run(command, cwd=snapshot.repo_root, check=False)
    duration = time.perf_counter() - start
    event_type = (
        EventType.VERIFICATION_PASSED
        if completed.returncode == 0
        else EventType.VERIFICATION_FAILED
    )
    status = "passed" if completed.returncode == 0 else "failed"
    finished_payload = dict(base)
    finished_payload.update(
        {
            "event_type": event_type,
            "verification_status": status,
            "verification_attempt": attempt,
            "verification_duration_seconds": round(duration, 3),
        }
    )
    finished_event = TelemetryEvent.model_validate(finished_payload).finalized()
    _emit(config, finished_event)
    return completed.returncode
