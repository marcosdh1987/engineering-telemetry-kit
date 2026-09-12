from __future__ import annotations

import json
import logging
from typing import Any

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
    event = TelemetryEvent(event_type=EventType.BRANCH_SNAPSHOT, repository="repo").finalized()

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
