from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from engobs import SCHEMA_VERSION
from engobs.domain.fingerprint import event_fingerprint
from engobs.privacy.validation import validate_no_forbidden_fields


class EventType(StrEnum):
    BRANCH_SNAPSHOT = "branch_snapshot"
    ACTIVITY_OBSERVED = "activity_observed"
    BRANCH_MERGED = "branch_merged"
    WORK_UNIT_DECLARED = "work_unit_declared"
    WORK_UNIT_COMPLETED = "work_unit_completed"
    WORK_UNIT_ABANDONED = "work_unit_abandoned"
    VERIFICATION_STARTED = "verification_started"
    VERIFICATION_PASSED = "verification_passed"
    VERIFICATION_FAILED = "verification_failed"
    AI_SESSION_STARTED = "ai_session_started"
    AI_SESSION_ENDED = "ai_session_ended"


class TelemetryEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = SCHEMA_VERSION
    event_id: str | None = None
    event_type: EventType
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    organization: str | None = None
    project: str | None = None
    repository: str | None = None
    branch: str | None = None
    work_unit_id: str | None = None
    git_head_sha: str | None = None
    git_base_sha: str | None = None
    commits_count: int | None = None
    new_commits: int | None = None
    files_changed_count: int | None = None
    lines_added: int | None = None
    lines_deleted: int | None = None
    dirty_files_count: int | None = None
    untracked_files_count: int | None = None
    dirty_lines_added: int | None = None
    dirty_lines_deleted: int | None = None
    verification_status: str | None = None
    verification_attempt: int | None = None
    verification_duration_seconds: float | None = None
    ai_tool: str | None = None
    opaque_session_id: str | None = None
    model: str | None = None
    trigger: str | None = None
    is_trunk: bool | None = None
    activity_window: str | None = None
    in_progress_activity: bool | None = None

    def finalized(self, *, bucket_seconds: int = 60) -> TelemetryEvent:
        payload = self.model_dump(mode="json", exclude_none=True)
        validate_no_forbidden_fields(payload)
        if self.event_id is None:
            payload["event_id"] = event_fingerprint(payload, bucket_seconds=bucket_seconds)
        return TelemetryEvent.model_validate(payload)
