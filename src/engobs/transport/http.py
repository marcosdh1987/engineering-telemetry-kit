from __future__ import annotations

import json
import logging
import ssl
from dataclasses import dataclass
from importlib import metadata
from typing import Any
from urllib import error, request

from engobs.config.models import ResolvedConfig
from engobs.domain.events import TelemetryEvent
from engobs.domain.wire import WireContractError, is_ai_observation, to_wire

LOGGER = logging.getLogger("engobs")
DISTRIBUTION_NAME = "engineering-telemetry-kit"
BODY_SNIPPET_BYTES = 512


def client_version() -> str:
    """Installed package version, or ``dev`` when metadata is unavailable (source checkout)."""
    try:
        return metadata.version(DISTRIBUTION_NAME)
    except metadata.PackageNotFoundError:
        return "dev"


USER_AGENT = f"engobs/{client_version()}"


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
    server: str | None = None
    body_snippet: str | None = None


def _ssl_context(config: ResolvedConfig) -> ssl.SSLContext:
    if not config.verify_tls:
        LOGGER.warning("ENGOBS_VERIFY_TLS=false; TLS verification disabled")
        return ssl._create_unverified_context()  # noqa: S323
    return ssl.create_default_context(cafile=config.ca_bundle)


def build_headers(config: ResolvedConfig, *, json_body: bool = False) -> dict[str, str]:
    """Single source of the client identity sent on every request.

    Reverse proxies and CDNs (e.g. Cloudflare browser-integrity checks) reject urllib's default
    ``Python-urllib/x.y`` User-Agent, so the client always identifies itself explicitly.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if json_body:
        headers["Content-Type"] = "application/json"
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Copy of ``headers`` safe for logs and diagnostics."""
    return {
        key: ("Bearer ******" if key.lower() == "authorization" else value)
        for key, value in headers.items()
    }


def _server_header(exc: error.HTTPError) -> str | None:
    headers = exc.headers
    if headers is None:
        return None
    value = headers.get("Server")
    if not value:
        return None
    return str(value).strip().lower() or None


def _snippet(raw: bytes) -> str | None:
    text = raw[:BODY_SNIPPET_BYTES].decode("utf-8", errors="replace").strip()
    return text or None


def _error_snippet(exc: error.HTTPError) -> str | None:
    try:
        return _snippet(exc.read(BODY_SNIPPET_BYTES))
    except Exception:  # noqa: BLE001
        return None


def _parse_json_object(raw: bytes) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw.decode() or "{}")
    except (ValueError, UnicodeDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _endpoint_for(event: TelemetryEvent, config: ResolvedConfig) -> str:
    base = (config.endpoint or "").rstrip("/")
    if is_ai_observation(event):
        return f"{base}/ai-observations"
    return f"{base}/events"


def send_event(config: ResolvedConfig, event: TelemetryEvent) -> DeliveryResult:
    if not config.enabled:
        return DeliveryResult(ok=True, status_code=None, message="disabled")
    if not config.endpoint:
        return DeliveryResult(ok=False, status_code=None, message="missing endpoint")

    try:
        payload = to_wire(event)
    except WireContractError as exc:
        LOGGER.warning("telemetry not sent event=%s reason=%s", event.event_type, exc)
        return DeliveryResult(ok=False, status_code=None, message=str(exc))
    body = json.dumps(payload).encode()
    target = _endpoint_for(event, config)
    headers = build_headers(config, json_body=True)
    req = request.Request(target, data=body, method="POST", headers=headers)
    try:
        with request.urlopen(
            req,
            timeout=config.timeout_seconds,
            context=_ssl_context(config),
        ) as response:
            status_code = response.getcode()
            LOGGER.debug(
                "sent event type=%s endpoint=%s status=%s headers=%s",
                event.event_type,
                target,
                status_code,
                redact_headers(headers),
            )
            return DeliveryResult(
                ok=200 <= status_code < 300,
                status_code=status_code,
                message="ok",
            )
    except error.HTTPError as exc:
        LOGGER.warning(
            "telemetry http error event=%s status=%s server=%s",
            event.event_type,
            exc.code,
            _server_header(exc) or "unknown",
        )
        # The server's own response (never our payload or headers) helps diagnose 4xx/5xx.
        LOGGER.debug("telemetry http error detail=%s", _error_snippet(exc))
        return DeliveryResult(
            ok=False,
            status_code=exc.code,
            message=f"HTTP {exc.code} {exc.reason}",
        )
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
    req = request.Request(target, method="GET", headers=build_headers(config))
    try:
        with request.urlopen(
            req,
            timeout=config.timeout_seconds,
            context=_ssl_context(config),
        ) as response:
            status_code = response.getcode()
            raw_body = response.read()
            ok = 200 <= status_code < 300
            payload = _parse_json_object(raw_body)
            if ok:
                message = "ok" if payload is not None else "ok (non-JSON body)"
            else:
                message = f"HTTP {status_code}"
            return HealthResult(
                ok=ok,
                status_code=status_code,
                payload=payload,
                message=message,
                body_snippet=None if ok else _snippet(raw_body),
            )
    except error.HTTPError as exc:
        return HealthResult(
            ok=False,
            status_code=exc.code,
            payload=None,
            message=f"HTTP {exc.code} {exc.reason}",
            server=_server_header(exc),
            body_snippet=_error_snippet(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return HealthResult(
            ok=False,
            status_code=None,
            payload=None,
            message=f"{exc.__class__.__name__}: {exc}",
        )
