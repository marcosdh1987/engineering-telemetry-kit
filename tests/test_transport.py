from __future__ import annotations

import email.message
import io
import json
import logging
import re
from typing import Any
from urllib import error

import pytest

from engobs.config.models import ResolvedConfig
from engobs.domain.events import EventType, TelemetryEvent
from engobs.transport import http as http_transport


class DummyResponse:
    def __init__(self, code: int, body: dict[str, Any] | None = None) -> None:
        self._code = code
        self._body = json.dumps(body or {}).encode()

    def __enter__(self) -> DummyResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def getcode(self) -> int:
        return self._code

    def read(self) -> bytes:
        return self._body


def _event(event_type: EventType) -> TelemetryEvent:
    return TelemetryEvent(
        event_type=event_type,
        organization="org",
        project="proj",
        repository="repo",
        branch="feature/x",
        ai_tool="claude" if event_type.value.startswith("ai_") else None,
    ).finalized()


def test_send_event_uses_bearer_auth_and_never_transmits_privacy_salt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float, context: object) -> DummyResponse:
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode())
        return DummyResponse(202)

    monkeypatch.setattr(http_transport.request, "urlopen", fake_urlopen)
    config = ResolvedConfig(
        endpoint="https://gateway.example.com",
        api_key="topsecret",
        privacy_salt="localsalt",
    )
    event = _event(EventType.BRANCH_SNAPSHOT)

    result = http_transport.send_event(config, event)

    assert result.ok
    assert captured["headers"]["Authorization"].startswith("Bearer ")
    assert captured["headers"]["Authorization"].endswith("topsecret")
    assert "privacy_salt" not in captured["body"]
    assert "api_key" not in captured["body"]


def test_tls_disable_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        http_transport.request,
        "urlopen",
        lambda *args, **kwargs: DummyResponse(200, {"ok": True}),
    )
    caplog.set_level(logging.WARNING)
    config = ResolvedConfig(endpoint="https://gateway.example.com", verify_tls=False)
    http_transport.check_health(config)
    assert "TLS verification disabled" in caplog.text


def test_non_2xx_health_response_is_not_treated_as_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        http_transport.request,
        "urlopen",
        lambda *args, **kwargs: DummyResponse(302, {"redirect": True}),
    )
    config = ResolvedConfig(endpoint="https://gateway.example.com")
    result = http_transport.check_health(config)
    assert not result.ok
    assert result.status_code == 302


def _lower_headers(req: Any) -> dict[str, str]:
    # urllib capitalizes header names (User-agent); compare case-insensitively.
    return {key.lower(): value for key, value in req.header_items()}


def _capturing_urlopen(captured: dict[str, Any]) -> Any:
    def fake_urlopen(req: Any, timeout: float, context: object) -> DummyResponse:
        captured["method"] = req.get_method()
        captured["url"] = req.full_url
        captured["headers"] = _lower_headers(req)
        return DummyResponse(200, {"status": "ok"})

    return fake_urlopen


def _health(config: ResolvedConfig) -> object:
    return http_transport.check_health(config)


def _events(config: ResolvedConfig) -> object:
    return http_transport.send_event(config, _event(EventType.BRANCH_SNAPSHOT))


def _ai_observations(config: ResolvedConfig) -> object:
    return http_transport.send_event(config, _event(EventType.AI_SESSION_STARTED))


@pytest.mark.parametrize(
    ("call", "method", "path", "json_body"),
    [
        (_health, "GET", "/health", False),
        (_events, "POST", "/events", True),
        (_ai_observations, "POST", "/ai-observations", True),
    ],
)
def test_every_request_sends_engobs_client_identity(
    monkeypatch: pytest.MonkeyPatch,
    call: Any,
    method: str,
    path: str,
    json_body: bool,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(http_transport.request, "urlopen", _capturing_urlopen(captured))
    config = ResolvedConfig(endpoint="https://gateway.example.com/")

    call(config)

    assert captured["method"] == method
    assert captured["url"] == f"https://gateway.example.com{path}"
    headers = captured["headers"]
    assert headers["user-agent"] == http_transport.USER_AGENT
    assert re.fullmatch(r"engobs/[0-9A-Za-z.+\-]+", headers["user-agent"])
    assert not headers["user-agent"].startswith("Python-urllib")
    assert headers["accept"] == "application/json"
    assert ("content-type" in headers) is json_body
    if json_body:
        assert headers["content-type"] == "application/json"
    assert "authorization" not in headers


@pytest.mark.parametrize("call", [_health, _events, _ai_observations])
def test_authorization_is_sent_only_when_api_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
    call: Any,
) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(http_transport.request, "urlopen", _capturing_urlopen(captured))

    call(ResolvedConfig(endpoint="https://gateway.example.com", api_key="topsecret"))

    assert captured["headers"]["authorization"] == "Bearer topsecret"


def test_user_agent_reports_installed_version_or_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    assert http_transport.USER_AGENT == f"engobs/{http_transport.client_version()}"

    def missing(name: str) -> str:
        raise http_transport.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(http_transport.metadata, "version", missing)
    assert http_transport.client_version() == "dev"


def test_redact_headers_masks_authorization_only() -> None:
    headers = http_transport.build_headers(
        ResolvedConfig(endpoint="https://gateway.example.com", api_key="topsecret"),
        json_body=True,
    )
    redacted = http_transport.redact_headers(headers)
    assert redacted["Authorization"] == "Bearer ******"
    assert redacted["User-Agent"] == http_transport.USER_AGENT
    assert "topsecret" not in json.dumps(redacted)
    assert headers["Authorization"] == "Bearer topsecret"  # original untouched


def _cloudflare_403(url: str) -> error.HTTPError:
    hdrs = email.message.Message()
    hdrs["Server"] = "cloudflare"
    return error.HTTPError(url, 403, "Forbidden", hdrs, io.BytesIO(b"error code: 1010"))


def test_http_error_logs_server_and_never_logs_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def raise_403(req: Any, timeout: float, context: object) -> DummyResponse:
        raise _cloudflare_403(req.full_url)

    monkeypatch.setattr(http_transport.request, "urlopen", raise_403)
    caplog.set_level(logging.DEBUG)
    config = ResolvedConfig(endpoint="https://gateway.example.com", api_key="topsecret")

    result = http_transport.send_event(config, _event(EventType.BRANCH_SNAPSHOT))

    assert not result.ok
    assert result.status_code == 403
    assert result.message == "HTTP 403 Forbidden"
    assert "telemetry http error event=branch_snapshot status=403 server=cloudflare" in caplog.text
    assert "topsecret" not in caplog.text


def test_check_health_captures_server_and_body_snippet_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_403(req: Any, timeout: float, context: object) -> DummyResponse:
        raise _cloudflare_403(req.full_url)

    monkeypatch.setattr(http_transport.request, "urlopen", raise_403)

    result = http_transport.check_health(ResolvedConfig(endpoint="https://gateway.example.com"))

    assert not result.ok
    assert result.status_code == 403
    assert result.message == "HTTP 403 Forbidden"
    assert result.server == "cloudflare"
    assert result.body_snippet == "error code: 1010"


def test_check_health_body_snippet_is_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_502(req: Any, timeout: float, context: object) -> DummyResponse:
        raise error.HTTPError(req.full_url, 502, "Bad Gateway", None, io.BytesIO(b"x" * 4096))

    monkeypatch.setattr(http_transport.request, "urlopen", raise_502)

    result = http_transport.check_health(ResolvedConfig(endpoint="https://gateway.example.com"))

    assert result.status_code == 502
    assert result.server is None
    assert result.body_snippet is not None
    assert len(result.body_snippet) == http_transport.BODY_SNIPPET_BYTES


def test_check_health_non_json_200_keeps_status(monkeypatch: pytest.MonkeyPatch) -> None:
    class HtmlResponse(DummyResponse):
        def read(self) -> bytes:
            return b"<html>ok</html>"

    monkeypatch.setattr(
        http_transport.request, "urlopen", lambda *args, **kwargs: HtmlResponse(200)
    )

    result = http_transport.check_health(ResolvedConfig(endpoint="https://gateway.example.com"))

    assert result.ok
    assert result.status_code == 200
    assert result.payload is None


def test_http_error_detail_is_logged_at_debug_without_payload(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def raise_422(req: Any, timeout: float, context: object) -> DummyResponse:
        raise error.HTTPError(
            req.full_url,
            422,
            "Unprocessable Entity",
            None,
            io.BytesIO(b'{"error":"invalid_payload"}'),
        )

    monkeypatch.setattr(http_transport.request, "urlopen", raise_422)
    caplog.set_level(logging.DEBUG)

    result = http_transport.send_event(
        ResolvedConfig(endpoint="https://gateway.example.com", api_key="topsecret"),
        _event(EventType.BRANCH_SNAPSHOT),
    )

    assert result.message == "HTTP 422 Unprocessable Entity"
    assert 'detail={"error":"invalid_payload"}' in caplog.text
    assert "topsecret" not in caplog.text
    assert "feature/x" not in caplog.text  # never the payload
