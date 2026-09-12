from __future__ import annotations

from engobs.config.models import PrivacyMode, ResolvedConfig
from engobs.domain.events import TelemetryEvent
from engobs.privacy.pseudonymize import stable_hash

STRICT_FIELDS = (
    "organization",
    "project",
    "repository",
    "branch",
    "work_unit_id",
    "git_head_sha",
    "git_base_sha",
    "opaque_session_id",
)


class StrictPrivacyError(ValueError):
    pass


def apply_privacy_mode(event: TelemetryEvent, config: ResolvedConfig) -> TelemetryEvent:
    if config.privacy_mode != PrivacyMode.STRICT:
        return event
    if not config.privacy_salt:
        raise StrictPrivacyError(
            "Strict mode requires ENGOBS_PRIVACY_SALT or a stored global privacy_salt"
        )

    data = event.model_dump()
    for field_name in STRICT_FIELDS:
        value = data.get(field_name)
        if value:
            data[field_name] = stable_hash(str(value), config.privacy_salt, namespace=field_name)
    return TelemetryEvent.model_validate(data)
