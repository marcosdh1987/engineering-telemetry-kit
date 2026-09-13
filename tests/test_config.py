from pathlib import Path

from engobs.config.loader import (
    ENV_MAP,
    describe_config_sources,
    load_config,
    write_global_config,
)
from engobs.config.models import FileConfig, PrivacyMode, ProfileConfig


def test_profile_and_precedence_resolution(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".engobs.toml").write_text(
        'profile = "company"\n'
        'project = "repo-project"\n'
        "[profiles.company]\n"
        'organization = "repo-org"\n'
    )
    global_config_path = tmp_path / "config.toml"
    write_global_config(
        global_config_path,
        FileConfig(
            profiles={
                "company": ProfileConfig(
                    endpoint="https://gateway.example.com",
                    privacy_mode=PrivacyMode.STRICT,
                    repository="global-repo",
                )
            }
        ),
    )
    monkeypatch.setenv("ENGOBS_PROJECT", "env-project")

    config = load_config(repo_root, global_config_path=global_config_path)

    assert config.profile == "company"
    assert config.endpoint == "https://gateway.example.com"
    assert config.organization == "repo-org"
    assert config.project == "env-project"
    assert config.repository == "global-repo"
    assert config.privacy_mode == PrivacyMode.STRICT


def test_cli_profile_override_has_priority_over_env_and_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".engobs.toml").write_text('profile = "repo"\n')
    global_config_path = tmp_path / "config.toml"
    write_global_config(
        global_config_path,
        FileConfig(
            profiles={
                "repo": ProfileConfig(endpoint="https://repo.example.com"),
                "cli": ProfileConfig(endpoint="https://cli.example.com"),
            }
        ),
    )
    monkeypatch.setenv("ENGOBS_PROFILE", "env")

    config = load_config(
        repo_root,
        cli_overrides={"profile": "cli"},
        global_config_path=global_config_path,
    )

    assert config.profile == "cli"
    assert config.endpoint == "https://cli.example.com"


def test_describe_config_sources_reports_provenance_without_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".engobs.toml").write_text(
        'profile = "company"\n[profiles.company]\nproject = "p"\n'
    )
    global_config_path = tmp_path / "config.toml"
    write_global_config(
        global_config_path,
        FileConfig(profiles={"company": ProfileConfig(endpoint="https://gateway.example.com")}),
    )
    monkeypatch.setenv("ENGOBS_API_KEY", "topsecret")
    monkeypatch.delenv("ENGOBS_PROFILE", raising=False)

    sources = describe_config_sources(repo_root, global_config_path=global_config_path)

    assert sources.repo_exists and sources.global_exists
    assert sources.profile == "company"
    assert sources.profile_in_global and sources.profile_in_repo
    assert "ENGOBS_API_KEY" in sources.env_vars
    assert "topsecret" not in repr(sources)


def test_describe_config_sources_repo_only(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".engobs.toml").write_text('endpoint = "https://gateway.example.com"\n')
    for name in ENV_MAP:
        monkeypatch.delenv(name, raising=False)

    sources = describe_config_sources(repo_root, global_config_path=tmp_path / "missing.toml")

    assert sources.repo_exists and not sources.global_exists
    assert sources.profile is None
    assert sources.env_vars == ()
