from __future__ import annotations

import json
import logging
import ssl
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from engobs.config.models import ResolvedConfig
from engobs.domain.events import EventType, TelemetryEvent

LOGGER = logging.getLogger("engobs")


@dataclass(frozen=True)
class DeliveryResult:
    ok: bool
    status_code: int | None
    message: str


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    status_code: int | None
    payload: dict[str, Any] | None
    message: str


def _ssl_context(config: ResolvedConfig) -> ssl.SSLContext:
    if not config.verify_tls:
        LOGGER.warning("ENGOBS_VERIFY_TLS=false; TLS verification disabled")
        return ssl._create_unverified_context()  # noqa: S323
    return ssl.create_default_context(cafile=config.ca_bundle)


def _headers(config: ResolvedConfig, *, redact: bool = False) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        bearer_prefix = "Bearer "
        token = "******" if redact else bearer_prefix + config.api_key
        headers["Authorization"] = token
    return headers


def _endpoint_for(event: TelemetryEvent, config: ResolvedConfig) -> str:
    base = (config.endpoint or "").rstrip("/")
    if event.event_type in {EventType.AI_SESSION_STARTED, EventType.AI_SESSION_ENDED}:
        return f"{base}/ai-observations"
    return f"{base}/events"


def send_event(config: ResolvedConfig, event: TelemetryEvent) -> DeliveryResult:
    if not config.enabled:
        return DeliveryResult(ok=True, status_code=None, message="disabled")
    if not config.endpoint:
        return DeliveryResult(ok=False, status_code=None, message="missing endpoint")

    payload = event.model_dump(mode="json", exclude_none=True)
    body = json.dumps(payload).encode()
    target = _endpoint_for(event, config)
    req = request.Request(target, data=body, method="POST", headers=_headers(config))
    try:
        with request.urlopen(
            req,
            timeout=config.timeout_seconds,
            context=_ssl_context(config),
        ) as response:
            status_code = response.getcode()
            LOGGER.debug(
                "sent event type=%s endpoint=%s status=%s",
                event.event_type,
                target,
                status_code,
            )
            return DeliveryResult(
                ok=200 <= status_code < 300,
                status_code=status_code,
                message="ok",
            )
    except error.HTTPError as exc:
        LOGGER.warning("telemetry http error event=%s status=%s", event.event_type, exc.code)
        return DeliveryResult(ok=False, status_code=exc.code, message=exc.reason)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning(
            "telemetry delivery failed event=%s error_type=%s",
            event.event_type,
            exc.__class__.__name__,
        )
        return DeliveryResult(
            ok=False,
            status_code=None,
            message=f"delivery failed ({exc.__class__.__name__})",
        )


def check_health(config: ResolvedConfig) -> HealthResult:
    if not config.endpoint:
        return HealthResult(ok=False, status_code=None, payload=None, message="missing endpoint")
    target = f"{config.endpoint.rstrip('/')}/health"
    req = request.Request(target, method="GET", headers=_headers(config))
    try:
        with request.urlopen(
            req,
            timeout=config.timeout_seconds,
            context=_ssl_context(config),
        ) as response:
            raw_body = response.read().decode() or "{}"
            payload = json.loads(raw_body)
            return HealthResult(
                ok=True,
                status_code=response.getcode(),
                payload=payload,
                message="ok",
            )
    except error.HTTPError as exc:
        return HealthResult(ok=False, status_code=exc.code, payload=None, message=exc.reason)
    except Exception as exc:  # noqa: BLE001
        return HealthResult(ok=False, status_code=None, payload=None, message=str(exc))
