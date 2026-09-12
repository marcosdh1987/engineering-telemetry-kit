from datetime import UTC, datetime

import pytest

from engobs.config.models import PrivacyMode, ResolvedConfig
from engobs.domain.events import EventType, TelemetryEvent
from engobs.privacy.policy import StrictPrivacyError, apply_privacy_mode
from engobs.privacy.validation import PrivacyValidationError, validate_no_forbidden_fields


def test_forbidden_fields_rejected_recursively() -> None:
    with pytest.raises(PrivacyValidationError):
        validate_no_forbidden_fields({"outer": {"prompt": "secret"}})


@pytest.mark.parametrize(
    "field_name",
    [
        "prompt",
        "completion",
        "transcript",
        "source",
        "source_code",
        "diff",
        "patch",
        "filename",
        "filepath",
        "commit_message",
        "developer_name",
        "email",
        "username",
        "api_key",
        "password",
        "secret",
        "remote_url",
        "stdout",
        "stderr",
    ],
)
def test_all_required_forbidden_fields_are_blocked(field_name: str) -> None:
    with pytest.raises(PrivacyValidationError):
        validate_no_forbidden_fields({field_name: "forbidden"})


def test_strict_mode_pseudonymizes_stably() -> None:
    config = ResolvedConfig(privacy_mode=PrivacyMode.STRICT, privacy_salt="salt")
    event = TelemetryEvent(
        event_type=EventType.BRANCH_SNAPSHOT,
        occurred_at=datetime.now(UTC),
        organization="marcosdh1987",
        project="engineering-telemetry-kit",
        repository="engineering-telemetry-kit",
        branch="feature/privacy",
        git_head_sha="abc123",
        git_base_sha="def456",
    ).finalized()

    first = apply_privacy_mode(event, config)
    second = apply_privacy_mode(event, config)

    assert first.repository == second.repository
    assert first.repository != "engineering-telemetry-kit"
    assert first.branch != "feature/privacy"
    assert first.git_head_sha != "abc123"


def test_strict_mode_requires_salt() -> None:
    config = ResolvedConfig(privacy_mode=PrivacyMode.STRICT)
    event = TelemetryEvent(event_type=EventType.BRANCH_SNAPSHOT).finalized()
    with pytest.raises(StrictPrivacyError):
        apply_privacy_mode(event, config)
