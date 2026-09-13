from __future__ import annotations

import email.message
import io
from pathlib import Path
from typing import Any
from urllib import error

import pytest

from engobs.commands.doctor import CLOUDFLARE_HINT, http_hints, run_doctor
from engobs.transport import http as http_transport
from engobs.transport.http import HealthResult


def _health(status: int | None, server: str | None = None, body: str | None = None) -> HealthResult:
    return HealthResult(
        ok=False,
        status_code=status,
        payload=None,
        message=f"HTTP {status}" if status else "URLError: boom",
        server=server,
        body_snippet=body,
    )


def test_http_hints_cloudflare_1010_from_server_header_or_body() -> None:
    assert CLOUDFLARE_HINT in http_hints(_health(403, server="cloudflare"))
    assert CLOUDFLARE_HINT in http_hints(_health(403, body="error code: 1010"))
    assert CLOUDFLARE_HINT not in http_hints(_health(403, server="nginx"))


@pytest.mark.parametrize(
    ("status", "fragment"),
    [
        (None, "connection failed"),
        (401, "ENGOBS_API_KEY"),
        (403, "reverse proxy/CDN"),
        (404, "base URL"),
        (502, "gateway error"),
    ],
)
def test_http_hints_by_status(status: int | None, fragment: str) -> None:
    hints = http_hints(_health(status))
    assert len(hints) == 1
    assert fragment in hints[0]


def _raise_cloudflare_403(req: Any, timeout: float, context: object) -> None:
    hdrs = email.message.Message()
    hdrs["Server"] = "cloudflare"
    raise error.HTTPError(req.full_url, 403, "Forbidden", hdrs, io.BytesIO(b"error code: 1010"))


def test_doctor_explains_cloudflare_block(
    git_repo: Path,
    isolated_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (git_repo / ".engobs.toml").write_text('endpoint = "https://gateway.example.com"\n')
    monkeypatch.setenv("ENGOBS_API_KEY", "topsecret")
    monkeypatch.setattr(http_transport.request, "urlopen", _raise_cloudflare_403)

    exit_code, diagnostics = run_doctor(git_repo, profile=None)
    out = capsys.readouterr().out

    assert exit_code == 0  # a blocked probe is a WARN, not a hard failure
    assert "WARN endpoint_reachable: HTTP 403 Forbidden" in out
    assert "HINT a reverse proxy/CDN may be blocking the engobs client" in out
    assert f"HINT {CLOUDFLARE_HINT}" in out
    assert "WARN auth: could not verify auth" in out
    assert "topsecret" not in out
    reachable = next(item for item in diagnostics if item.name == "endpoint_reachable")
    assert CLOUDFLARE_HINT in reachable.hints


def test_doctor_repo_only_config_is_not_a_warning(
    git_repo: Path,
    isolated_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (git_repo / ".engobs.toml").write_text('endpoint = "https://gateway.example.com"\n')
    monkeypatch.setattr(http_transport.request, "urlopen", _raise_cloudflare_403)

    exit_code, _ = run_doctor(git_repo, profile=None)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "OK configuration_source: repo=.engobs.toml (profile=default)" in out
    assert "OK repo_config:" in out
    assert "INFO global_config: not configured (optional)" in out
    assert "WARN global_config" not in out
    assert "WARN repo_config" not in out


def test_doctor_shows_global_profile_and_repo_overrides(
    git_repo: Path,
    isolated_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text('[profiles.company]\nendpoint = "https://gateway.example.com"\n')
    (git_repo / ".engobs.toml").write_text('profile = "company"\nproject = "demo"\n')
    monkeypatch.setattr(http_transport.request, "urlopen", _raise_cloudflare_403)

    run_doctor(git_repo, profile=None)
    out = capsys.readouterr().out

    assert (
        f"OK configuration_source: global={isolated_config} "
        "repo overrides=.engobs.toml (profile=company)"
    ) in out
    assert "OK global_config:" in out


def test_doctor_warns_on_unknown_profile_and_missing_endpoint(
    git_repo: Path,
    isolated_config: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (git_repo / ".engobs.toml").write_text('profile = "ghost"\n')

    exit_code, _ = run_doctor(git_repo, profile=None)
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "WARN profile: profile 'ghost' selected but not defined" in out
    assert "ERROR endpoint_configured: missing" in out
    assert "HINT set ENGOBS_ENDPOINT" in out


def test_doctor_incomplete_identity_is_an_error(
    git_repo: Path,
    isolated_config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import subprocess

    subprocess.run(["git", "remote", "remove", "origin"], cwd=git_repo, check=True)
    (git_repo / ".engobs.toml").write_text('endpoint = "https://gateway.example.com"\n')
    monkeypatch.setattr(http_transport.request, "urlopen", _raise_cloudflare_403)

    exit_code, _ = run_doctor(git_repo, profile=None)
    out = capsys.readouterr().out

    assert exit_code == 1
    assert "ERROR repository_identity: organization=None project=None repository=None" in out
    assert "HINT set organization/project/repository" in out
