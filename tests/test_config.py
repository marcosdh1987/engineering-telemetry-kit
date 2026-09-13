from pathlib import Path

from engobs.config.loader import load_config, write_global_config
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
