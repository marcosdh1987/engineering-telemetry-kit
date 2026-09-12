from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any, Callable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found, no-redef]

from engobs.config.models import FileConfig, PrivacyMode, ProfileConfig, ResolvedConfig

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "privacy_mode": PrivacyMode.STANDARD.value,
    "timeout_seconds": 1.5,
    "verify_tls": True,
    "debug": False,
    "heartbeat_seconds": 300,
}

SECRET_FIELDS = {"api_key", "privacy_salt"}
Parser = Callable[[str], Any]
ENV_MAP: dict[str, tuple[str, Parser]] = {
    "ENGOBS_ENABLED": ("enabled", lambda value: value.lower() == "true"),
    "ENGOBS_ENDPOINT": ("endpoint", str),
    "ENGOBS_API_KEY": ("api_key", str),
    "ENGOBS_ORGANIZATION": ("organization", str),
    "ENGOBS_PROJECT": ("project", str),
    "ENGOBS_REPOSITORY": ("repository", str),
    "ENGOBS_PRIVACY_MODE": ("privacy_mode", str),
    "ENGOBS_PRIVACY_SALT": ("privacy_salt", str),
    "ENGOBS_TIMEOUT_SECONDS": ("timeout_seconds", float),
    "ENGOBS_VERIFY_TLS": ("verify_tls", lambda value: value.lower() == "true"),
    "ENGOBS_CA_BUNDLE": ("ca_bundle", str),
    "ENGOBS_DEBUG": ("debug", lambda value: value.lower() == "true"),
    "ENGOBS_HEARTBEAT_SECONDS": ("heartbeat_seconds", int),
    "ENGOBS_PROFILE": ("profile", str),
}


def default_global_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home) / "engobs" / "config.toml"
    return Path.home() / ".config" / "engobs" / "config.toml"


def repo_config_path(repo_root: Path) -> Path:
    return repo_root / ".engobs.toml"


def load_toml_file(path: Path) -> FileConfig:
    if not path.exists():
        return FileConfig()
    data = tomllib.loads(path.read_text())
    return FileConfig.model_validate(data)


def _model_overlay(model: FileConfig) -> dict[str, Any]:
    data = model.model_dump(exclude_none=True)
    data.pop("profiles", None)
    return data


def _profile_overlay(model: FileConfig, profile_name: str | None) -> dict[str, Any]:
    if not profile_name:
        return {}
    profile = model.profiles.get(profile_name)
    if profile is None:
        return {}
    return profile.model_dump(exclude_none=True)


def env_overrides() -> dict[str, Any]:
    resolved: dict[str, Any] = {}
    for env_name, (field_name, parser) in ENV_MAP.items():
        raw = os.environ.get(env_name)
        if raw is None or raw == "":
            continue
        resolved[field_name] = parser(raw)
    return resolved


def _compact(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in mapping.items() if value is not None}


def load_config(
    repo_root: Path,
    *,
    profile_override: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    global_config_path: Path | None = None,
) -> ResolvedConfig:
    cli_overrides = cli_overrides or {}
    global_path = global_config_path or default_global_config_path()
    global_config = load_toml_file(global_path)
    repo_config = load_toml_file(repo_config_path(repo_root))
    env_config = env_overrides()

    selected_profile = (
        profile_override
        or env_config.get("profile")
        or repo_config.profile
        or global_config.profile
        or cli_overrides.get("profile")
    )

    merged: dict[str, Any] = {}
    merged.update(DEFAULTS)
    merged.update(_model_overlay(global_config))
    merged.update(_profile_overlay(global_config, selected_profile))
    merged.update(_model_overlay(repo_config))
    merged.update(_profile_overlay(repo_config, selected_profile))
    merged.update(env_config)
    merged.update(_compact(cli_overrides))
    merged["profile"] = selected_profile
    return ResolvedConfig.model_validate(merged)


def redact_config(config: ResolvedConfig) -> dict[str, Any]:
    data = config.model_dump()
    for field in SECRET_FIELDS:
        if data.get(field):
            data[field] = "***REDACTED***"
    return data


def toml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_global_config(path: Path, data: FileConfig) -> None:
    lines: list[str] = []
    base = _model_overlay(data)
    profiles = data.profiles
    for key, value in base.items():
        if key == "profile":
            continue
        lines.append(f"{key} = {toml_scalar(value)}")
    if data.profile is not None:
        lines.append(f"profile = {toml_scalar(data.profile)}")
    for profile_name in sorted(profiles):
        profile_data = profiles[profile_name].model_dump(exclude_none=True)
        if not profile_data:
            continue
        if lines:
            lines.append("")
        lines.append(f"[profiles.{profile_name}]")
        for key, value in profile_data.items():
            lines.append(f"{key} = {toml_scalar(value)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def ensure_privacy_salt(global_config_path: Path, profile_name: str | None = None) -> str:
    config = load_toml_file(global_config_path)
    if profile_name:
        profile = config.profiles.get(profile_name)
        if profile and profile.privacy_salt:
            return profile.privacy_salt
    if config.privacy_salt:
        return config.privacy_salt

    generated = secrets.token_hex(16)
    if profile_name:
        profile = config.profiles.get(profile_name)
        if profile is None:
            profile = ProfileConfig()
            config.profiles[profile_name] = profile
        profile.privacy_salt = generated
    else:
        config.privacy_salt = generated
    write_global_config(global_config_path, config)
    return generated
