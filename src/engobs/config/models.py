from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PrivacyMode(StrEnum):
    STANDARD = "standard"
    STRICT = "strict"
    CUSTOM = "custom"


class ProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint: str | None = None
    api_key: str | None = None
    organization: str | None = None
    project: str | None = None
    repository: str | None = None
    privacy_mode: PrivacyMode | None = None
    privacy_salt: str | None = None
    enabled: bool | None = None
    timeout_seconds: float | None = None
    verify_tls: bool | None = None
    ca_bundle: str | None = None
    debug: bool | None = None
    heartbeat_seconds: int | None = None


class FileConfig(ProfileConfig):
    profile: str | None = None
    profiles: dict[str, ProfileConfig] = Field(default_factory=dict)


class ResolvedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str | None = None
    endpoint: str | None = None
    api_key: str | None = None
    organization: str | None = None
    project: str | None = None
    repository: str | None = None
    privacy_mode: PrivacyMode = PrivacyMode.STANDARD
    privacy_salt: str | None = None
    enabled: bool = True
    timeout_seconds: float = 1.5
    verify_tls: bool = True
    ca_bundle: str | None = None
    debug: bool = False
    heartbeat_seconds: int = 300
