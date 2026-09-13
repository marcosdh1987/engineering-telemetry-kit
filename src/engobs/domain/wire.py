"""Wire adapter: engobs' flat ``TelemetryEvent`` -> the collector's schema v4 contract.

The Engineering Gateway collector (``ai-gateway`` ``engineering/contract.py``) accepts a closed
envelope with a typed ``attributes`` object and keeps two families apart: ``DevelopmentEvent``
(``POST /events``) and ``AiObservation`` (``POST /ai-observations``). engobs builds and
privacy-checks a flat event internally; this module is the single place that knows the wire
shape, so the collector's rules (field names, nesting, work-unit derivation) live here only.

``work_unit_id`` is a UUID5 in a namespace shared by every emitter, derived from
``repository:branch`` (or ``repository:branch@<UTC day>`` on trunk). It is derived from the
values *as sent* — pseudonymized in strict mode — so a snapshot and an AI observation for the
same branch still land on the same unit.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from engobs.domain.events import EventType, TelemetryEvent
from engobs.privacy.validation import validate_no_forbidden_fields

#: Shared with every emitter and the backend; changing it orphans every recorded unit.
WORK_UNIT_NAMESPACE = uuid.UUID("5f7c2a2e-6c1a-4b58-9f2e-3a9d4b2c1e01")
#: engobs' own event fingerprint is a SHA-256 hex; the collector stores ``event_id`` as a UUID.
EVENT_ID_NAMESPACE = uuid.uuid5(WORK_UNIT_NAMESPACE, "engobs-event-id")
TELEMETRY_SCOPE = "development"
AI_OBSERVATION_TYPES = frozenset({EventType.AI_SESSION_STARTED, EventType.AI_SESSION_ENDED})


class WireContractError(ValueError):
    """The event cannot be expressed in the collector contract (missing dimensions)."""


def derive_work_unit_id(repository: str, branch: str) -> str:
    return str(uuid.uuid5(WORK_UNIT_NAMESPACE, f"{repository}:{branch}"))


def derive_trunk_work_unit_id(repository: str, branch: str, window: str) -> str:
    return str(uuid.uuid5(WORK_UNIT_NAMESPACE, f"{repository}:{branch}@{window}"))


def wire_event_id(event_id: str | None) -> str:
    """A UUID for the collector's primary key, deterministic from engobs' fingerprint."""
    if not event_id:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(event_id))
    except ValueError:
        return str(uuid.uuid5(EVENT_ID_NAMESPACE, event_id))


def trunk_window_label(occurred_at: datetime) -> str:
    """Trunk work is windowed by UTC calendar day so its unit closes on its own."""
    return occurred_at.astimezone(UTC).date().isoformat()


def is_ai_observation(event: TelemetryEvent) -> bool:
    return event.event_type in AI_OBSERVATION_TYPES


def _compact(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in mapping.items() if value is not None}


def _in_progress_activity(event: TelemetryEvent) -> dict[str, int] | None:
    counts = (
        event.dirty_files_count,
        event.untracked_files_count,
        event.dirty_lines_added,
        event.dirty_lines_deleted,
    )
    if all(value is None for value in counts):
        return None
    return {
        "dirty_files_count": event.dirty_files_count or 0,
        "untracked_files_count": event.untracked_files_count or 0,
        "lines_added": event.dirty_lines_added or 0,
        "lines_deleted": event.dirty_lines_deleted or 0,
    }


def to_wire(event: TelemetryEvent) -> dict[str, Any]:
    """Serialize ``event`` exactly as the collector expects it. Raises on missing dimensions."""
    missing = [
        name for name in ("organization", "project", "repository") if not getattr(event, name)
    ]
    if missing:
        raise WireContractError(
            "cannot send telemetry without " + ", ".join(missing) + ": set them in "
            ".engobs.toml (or ENGOBS_ORGANIZATION / ENGOBS_PROJECT) or add a git remote"
        )
    organization = str(event.organization)
    project = str(event.project)
    repository = str(event.repository)
    branch = event.branch
    is_trunk = bool(event.is_trunk)
    window = trunk_window_label(event.occurred_at) if is_trunk else None

    if branch and window:
        work_unit_id = derive_trunk_work_unit_id(repository, branch, window)
    elif branch:
        work_unit_id = derive_work_unit_id(repository, branch)
    else:
        work_unit_id = event.work_unit_id or derive_work_unit_id(repository, "HEAD")

    envelope: dict[str, Any] = {
        "event_id": wire_event_id(event.event_id),
        "schema_version": event.schema_version,
        "telemetry_scope": TELEMETRY_SCOPE,
        "occurred_at": event.occurred_at.isoformat(),
        "organization": organization,
        "project": project,
        "repository": repository,
        "branch": branch,
        "work_unit_id": work_unit_id,
    }

    if is_ai_observation(event):
        wire = {
            **envelope,
            "observation_type": event.event_type.value,
            "tool": (event.ai_tool or "unknown").strip().lower(),
            "session_id": event.opaque_session_id,
            "model": event.model,
            "attributes": _compact({"is_trunk": is_trunk, "activity_window": window}),
        }
    else:
        attributes = _compact(
            {
                "trigger": event.trigger,
                "is_trunk": is_trunk,
                "activity_window": window,
                "git_base_sha": event.git_base_sha,
                "git_head_sha": event.git_head_sha,
                "commits_count": event.commits_count,
                "new_commits": event.new_commits,
                "files_changed_count": event.files_changed_count,
                "lines_added": event.lines_added,
                "lines_deleted": event.lines_deleted,
                "in_progress_activity": _in_progress_activity(event),
                "attempt": event.verification_attempt,
                "duration_seconds": event.verification_duration_seconds,
            }
        )
        wire = {**envelope, "event_type": event.event_type.value, "attributes": attributes}

    wire = _compact(wire)
    validate_no_forbidden_fields(wire)
    return wire
