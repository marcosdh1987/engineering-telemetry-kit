from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def bucket_timestamp(occurred_at: datetime, *, bucket_seconds: int) -> str:
    epoch = int(occurred_at.replace(tzinfo=UTC).timestamp())
    bucket = epoch - (epoch % bucket_seconds)
    return datetime.fromtimestamp(bucket, tz=UTC).isoformat()


def event_fingerprint(payload: dict[str, Any], *, bucket_seconds: int = 60) -> str:
    normalized = dict(payload)
    occurred_at = datetime.fromisoformat(str(normalized["occurred_at"]))
    normalized["occurred_at_bucket"] = bucket_timestamp(occurred_at, bucket_seconds=bucket_seconds)
    normalized.pop("occurred_at", None)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
