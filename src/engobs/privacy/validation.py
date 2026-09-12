from __future__ import annotations

from typing import Any

FORBIDDEN_KEYS = {
    "developer_name",
    "employee_name",
    "email",
    "username",
    "user_id",
    "employee_id",
    "prompt",
    "completion",
    "transcript",
    "chat_history",
    "source",
    "source_code",
    "diff",
    "patch",
    "file_content",
    "filename",
    "filepath",
    "absolute_path",
    "relative_path",
    "commit_message",
    "environment_variables",
    "env_dump",
    "stdout",
    "stderr",
    "terminal_output",
    "api_key",
    "password",
    "secret",
    "credential",
    "access_token",
    "refresh_token",
    "remote_url",
    "git_remote_url",
}


class PrivacyValidationError(ValueError):
    pass


def validate_no_forbidden_fields(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_KEYS:
                raise PrivacyValidationError(f"Forbidden field at {path}.{key}")
            validate_no_forbidden_fields(nested, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            validate_no_forbidden_fields(item, path=f"{path}[{index}]")
