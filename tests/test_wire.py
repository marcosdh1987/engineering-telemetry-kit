"""Wire contract tests: engobs events must land in the collector's schema v4 shape."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from engobs.config.models import PrivacyMode, ResolvedConfig
from engobs.domain.events import EventType, TelemetryEvent
from engobs.domain.wire import (
    WORK_UNIT_NAMESPACE,
    WireContractError,
    derive_trunk_work_unit_id,
    derive_work_unit_id,
    to_wire,
)
from engobs.privacy.policy import apply_privacy_mode

# Mirror of ai-gateway ``src/ai_gateway/engineering/contract.py`` (schema v4). Update both.
ENVELOPE_KEYS = {
    "event_id",
    "schema_version",
    "telemetry_scope",
    "occurred_at",
    "organization",
    "project",
    "repository",
    "branch",
    "work_unit_id",
}
DEVELOPMENT_ATTRIBUTE_KEYS = {
    "trigger",
    "work_unit_source",
    "is_trunk",
    "activity_window",
    "trunk",
    "trunk_resolved",
    "git_base_sha",
    "git_head_sha",
    "commits_count",
    "merge_commits_count",
    "new_commits",
    "files_changed_count",
    "lines_added",
    "lines_deleted",
    "first_commit_at",
    "last_commit_at",
    "previous_activity_at",
    "in_progress_activity",
    "ai_instrumented",
    "instrumentation",
    "completion_source",
    "declared_ai_status",
    "ai_tool",
    "ai_model",
    "task_id",
    "issue_id",
    "attempt",
    "duration_seconds",
    "verification_attempts",
    "verification_failures",
    "pull_request_number",
    "ci_run_id",
    "deployment_id",
    "environment",
}
IN_PROGRESS_KEYS = {"dirty_files_count", "untracked_files_count", "lines_added", "lines_deleted"}
AI_OBSERVATION_KEYS = ENVELOPE_KEYS | {
    "observation_type",
    "tool",
    "session_id",
    "provider",
    "model",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "attributes",
}
AI_ATTRIBUTE_KEYS = {"is_trunk", "activity_window"}
SNAPSHOT_TRIGGERS = {
    "commit",
    "checkout",
    "ai_session_start",
    "ai_turn",
    "ai_session_end",
    "manual",
}

OCCURRED_AT = datetime(2026, 9, 12, 23, 30, tzinfo=UTC)


def _snapshot(**overrides: object) -> TelemetryEvent:
    payload: dict[str, object] = {
        "event_type": EventType.BRANCH_SNAPSHOT,
        "occurred_at": OCCURRED_AT,
        "organization": "acme",
        "project": "payments",
        "repository": "payments-api",
        "branch": "feature/x",
        "work_unit_id": "payments-api:feature/x",
        "git_head_sha": "a" * 40,
        "git_base_sha": "b" * 40,
        "commits_count": 3,
        "new_commits": 1,
        "files_changed_count": 4,
        "lines_added": 50,
        "lines_deleted": 5,
        "dirty_files_count": 2,
        "untracked_files_count": 1,
        "dirty_lines_added": 7,
        "dirty_lines_deleted": 0,
        "is_trunk": False,
        "trigger": "manual",
        "activity_window": "300s",
        "in_progress_activity": True,
    }
    payload.update(overrides)
    return TelemetryEvent.model_validate(payload).finalized()


def test_branch_snapshot_uses_envelope_and_typed_attributes() -> None:
    wire = to_wire(_snapshot())

    assert set(wire) == ENVELOPE_KEYS | {"event_type", "attributes"}
    assert wire["telemetry_scope"] == "development"
    assert wire["schema_version"] == 4
    assert wire["event_type"] == "branch_snapshot"
    assert wire["occurred_at"] == "2026-09-12T23:30:00+00:00"
    assert set(wire["attributes"]) <= DEVELOPMENT_ATTRIBUTE_KEYS
    assert wire["attributes"]["trigger"] in SNAPSHOT_TRIGGERS
    assert wire["attributes"]["is_trunk"] is False
    assert "activity_window" not in wire["attributes"]
    assert wire["attributes"]["lines_added"] == 50
    assert wire["attributes"]["in_progress_activity"] == {
        "dirty_files_count": 2,
        "untracked_files_count": 1,
        "lines_added": 7,
        "lines_deleted": 0,
    }
    assert set(wire["attributes"]["in_progress_activity"]) == IN_PROGRESS_KEYS
    # Flat-only fields never leak onto the wire.
    for key in ("dirty_lines_added", "verification_status", "opaque_session_id", "ai_tool"):
        assert key not in wire and key not in wire["attributes"]


def test_event_id_is_a_deterministic_uuid() -> None:
    event = _snapshot()
    assert event.event_id is not None and len(event.event_id) == 64  # engobs sha256 fingerprint

    first = to_wire(event)["event_id"]

    assert uuid.UUID(first).version == 5  # the collector stores event_id as a UUID
    assert to_wire(event)["event_id"] == first
    assert to_wire(_snapshot(trigger="commit"))["event_id"] != first


def test_work_unit_id_is_uuid5_in_the_shared_namespace() -> None:
    wire = to_wire(_snapshot())

    expected = str(uuid.uuid5(WORK_UNIT_NAMESPACE, "payments-api:feature/x"))
    assert wire["work_unit_id"] == expected == derive_work_unit_id("payments-api", "feature/x")
    assert str(WORK_UNIT_NAMESPACE) == "5f7c2a2e-6c1a-4b58-9f2e-3a9d4b2c1e01"


def test_trunk_snapshot_is_windowed_by_utc_day() -> None:
    wire = to_wire(_snapshot(branch="main", is_trunk=True))

    assert wire["attributes"]["is_trunk"] is True
    assert wire["attributes"]["activity_window"] == "2026-09-12"
    assert wire["work_unit_id"] == derive_trunk_work_unit_id("payments-api", "main", "2026-09-12")


def test_verification_event_maps_attempt_and_duration() -> None:
    event = TelemetryEvent(
        event_type=EventType.VERIFICATION_PASSED,
        organization="acme",
        project="payments",
        repository="payments-api",
        branch="feature/x",
        verification_status="passed",
        verification_attempt=2,
        verification_duration_seconds=12.5,
    ).finalized()

    wire = to_wire(event)

    assert wire["event_type"] == "verification_passed"
    assert wire["attributes"] == {"is_trunk": False, "attempt": 2, "duration_seconds": 12.5}


def test_ai_session_becomes_an_ai_observation() -> None:
    event = TelemetryEvent(
        event_type=EventType.AI_SESSION_STARTED,
        occurred_at=OCCURRED_AT,
        organization="acme",
        project="payments",
        repository="payments-api",
        branch="main",
        is_trunk=True,
        ai_tool="Claude",
        model="claude-sonnet-5",
        opaque_session_id="deadbeef",
        trigger="ai_turn",
    ).finalized()

    wire = to_wire(event)

    assert set(wire) <= AI_OBSERVATION_KEYS
    assert "event_type" not in wire and "trigger" not in wire
    assert wire["observation_type"] == "ai_session_started"
    assert wire["tool"] == "claude"
    assert wire["session_id"] == "deadbeef"
    assert wire["model"] == "claude-sonnet-5"
    assert wire["attributes"] == {"is_trunk": True, "activity_window": "2026-09-12"}
    assert set(wire["attributes"]) <= AI_ATTRIBUTE_KEYS
    # Same branch, same day -> same unit as the git snapshot.
    assert wire["work_unit_id"] == to_wire(_snapshot(branch="main", is_trunk=True))["work_unit_id"]


def test_strict_mode_derives_unit_from_pseudonymized_identity() -> None:
    config = ResolvedConfig(privacy_mode=PrivacyMode.STRICT, privacy_salt="localsalt")
    snapshot = apply_privacy_mode(_snapshot(), config)
    observation = apply_privacy_mode(
        TelemetryEvent(
            event_type=EventType.AI_SESSION_ENDED,
            organization="acme",
            project="payments",
            repository="payments-api",
            branch="feature/x",
            ai_tool="claude",
        ).finalized(),
        config,
    )

    snapshot_wire = to_wire(snapshot)
    observation_wire = to_wire(observation)

    assert snapshot_wire["repository"] != "payments-api"
    assert snapshot_wire["branch"] != "feature/x"
    assert snapshot_wire["work_unit_id"] == derive_work_unit_id(
        str(snapshot.repository), str(snapshot.branch)
    )
    assert snapshot_wire["work_unit_id"] == observation_wire["work_unit_id"]
    assert "payments-api" not in str(snapshot_wire)


@pytest.mark.parametrize("missing", ["organization", "project", "repository"])
def test_missing_dimension_is_a_contract_error(missing: str) -> None:
    with pytest.raises(WireContractError, match=missing):
        to_wire(_snapshot(**{missing: None}))
