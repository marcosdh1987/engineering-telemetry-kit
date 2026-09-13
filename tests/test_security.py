from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import pytest

from engobs.cli import main
from engobs.state.store import load_state
from engobs.transport.http import DeliveryResult

REMOTE_URL = "git@github.com:marcosdh1987/engineering-telemetry-kit.git"
FORBIDDEN_KEYS = {
    "developer_name",
    "email",
    "username",
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
    "api_key",
    "password",
    "secret",
    "remote_url",
    "stdout",
    "stderr",
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _init_repo(path: Path) -> None:
    _git(path, "init", "-b", "main")
    _git(path, "config", "user.name", "Tester")
    _git(path, "config", "user.email", "tester@example.com")
    (path / "README.md").write_text("hi\n")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "init")
    _git(path, "remote", "add", "origin", REMOTE_URL)
    _git(path, "checkout", "-b", "feature/privacy")
    (path / "README.md").write_text("hi\nmore\n")
    (path / "draft.txt").write_text("draft\n")


def test_snapshot_payload_excludes_forbidden_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")

    captured: list[dict[str, Any]] = []

    def fake_send_event(config: Any, event: Any) -> DeliveryResult:
        del config
        captured.append(event.model_dump(mode="json", exclude_none=True))
        return DeliveryResult(ok=True, status_code=202, message="ok")

    monkeypatch.setattr("engobs.commands.snapshot.send_event", fake_send_event)

    assert main(["snapshot", "--force"]) == 0
    assert captured
    serialized = json.dumps(captured)
    assert "tester@example.com" not in serialized
    assert REMOTE_URL not in serialized
    for payload in captured:
        assert FORBIDDEN_KEYS.isdisjoint(payload)
        assert payload["repository"] == "engineering-telemetry-kit"
        assert payload["branch"] == "feature/privacy"


def test_strict_snapshot_pseudonymizes_repo_branch_and_sha(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")
    monkeypatch.setenv("ENGOBS_PRIVACY_MODE", "strict")
    monkeypatch.setenv("ENGOBS_PRIVACY_SALT", "localsalt")

    captured: list[dict[str, Any]] = []

    def fake_send_event(config: Any, event: Any) -> DeliveryResult:
        del config
        captured.append(event.model_dump(mode="json", exclude_none=True))
        return DeliveryResult(ok=True, status_code=202, message="ok")

    monkeypatch.setattr("engobs.commands.snapshot.send_event", fake_send_event)

    assert main(["snapshot", "--force"]) == 0
    assert captured
    for payload in captured:
        assert payload["repository"] != "engineering-telemetry-kit"
        assert payload["branch"] != "feature/privacy"
        assert payload["git_head_sha"]
        assert payload["git_head_sha"] != _git_head_sha(repo)


def _git_head_sha(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_debug_logging_redacts_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from engobs.config.models import ResolvedConfig
    from engobs.domain.events import EventType, TelemetryEvent
    from engobs.transport import http as http_transport

    class DummyResponse:
        def __enter__(self) -> DummyResponse:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def getcode(self) -> int:
            return 202

    monkeypatch.setattr(
        http_transport.request,
        "urlopen",
        lambda *args, **kwargs: DummyResponse(),
    )
    caplog.set_level(logging.DEBUG)
    config = ResolvedConfig(endpoint="https://gateway.example.com", api_key="topsecret")
    event = TelemetryEvent(
        event_type=EventType.BRANCH_SNAPSHOT,
        organization="org",
        project="proj",
        repository="repo",
        branch="main",
    ).finalized()

    result = http_transport.send_event(config, event)

    assert result.ok
    assert "topsecret" not in caplog.text


def test_force_snapshot_bypasses_heartbeat_suppression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")

    captured: list[dict[str, Any]] = []

    def fake_send_event(config: Any, event: Any) -> DeliveryResult:
        del config
        captured.append(event.model_dump(mode="json", exclude_none=True))
        return DeliveryResult(ok=True, status_code=202, message="ok")

    monkeypatch.setattr("engobs.commands.snapshot.send_event", fake_send_event)
    monkeypatch.setattr("engobs.commands.snapshot.should_emit_heartbeat", lambda *args: False)

    assert main(["snapshot", "--force"]) == 0
    assert {payload["event_type"] for payload in captured} == {
        "branch_snapshot",
        "activity_observed",
    }


def test_failed_snapshot_does_not_advance_local_snapshot_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")

    def fake_send_event(config: Any, event: Any) -> DeliveryResult:
        del config, event
        return DeliveryResult(ok=False, status_code=503, message="unavailable")

    monkeypatch.setattr("engobs.commands.snapshot.send_event", fake_send_event)

    assert main(["snapshot", "--force"]) == 0
    state = load_state(repo)
    assert "last_snapshot_fingerprint" not in state


def test_snapshot_state_tracks_branch_snapshot_fingerprint_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")

    captured: list[dict[str, Any]] = []

    def fake_send_event(config: Any, event: Any) -> DeliveryResult:
        del config
        captured.append(event.model_dump(mode="json", exclude_none=True))
        return DeliveryResult(ok=True, status_code=202, message="ok")

    monkeypatch.setattr("engobs.commands.snapshot.send_event", fake_send_event)

    assert main(["snapshot", "--force"]) == 0
    state = load_state(repo)
    branch_event = next(
        payload for payload in captured if payload["event_type"] == "branch_snapshot"
    )
    assert state["last_snapshot_fingerprint"] == branch_event["event_id"]


def test_failed_ai_session_does_not_advance_local_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")

    def fake_send_event(config: Any, event: Any) -> DeliveryResult:
        del config, event
        return DeliveryResult(ok=False, status_code=503, message="unavailable")

    monkeypatch.setattr("engobs.commands.ai_session.send_event", fake_send_event)

    assert (
        main(
            [
                "ai-session",
                "start",
                "--tool",
                "claude",
                "--session-id",
                "session-123",
            ]
        )
        == 0
    )
    state = load_state(repo)
    assert state.get("ai_sessions") is None


def test_verify_start_failure_does_not_advance_attempt_counter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("ENGOBS_ENDPOINT", "https://gateway.example.com")

    assert main(["verify", "--", "/definitely/missing-command"]) == 127
    state = load_state(repo)
    assert "verification_attempt" not in state
