from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engobs import SCHEMA_VERSION
from engobs.ai.claude import claude_hooks_installed, claude_settings_path
from engobs.commands.common import configure_logging, load_runtime_config
from engobs.config.loader import default_global_config_path, repo_config_path
from engobs.config.models import PrivacyMode
from engobs.git.context import GitError, get_snapshot
from engobs.git.hooks import HOOK_TRIGGERS, hook_installed
from engobs.transport.http import check_health


@dataclass(frozen=True)
class Diagnostic:
    status: str
    name: str
    detail: str


def run_doctor(
    cwd: Path,
    *,
    profile: str | None,
    emit_output: bool = True,
) -> tuple[int, list[Diagnostic]]:
    try:
        snapshot = get_snapshot(cwd)
    except GitError as exc:
        error_diagnostics = [Diagnostic("ERROR", "git_repository", str(exc))]
        if emit_output:
            for item in error_diagnostics:
                print(f"{item.status} {item.name}: {item.detail}")
        return 1, error_diagnostics

    config, repo_root = load_runtime_config(cwd, profile)
    configure_logging(config.debug)
    diagnostics: list[Diagnostic] = []

    global_path = default_global_config_path()
    diagnostics.append(
        Diagnostic(
            "OK" if global_path.exists() else "WARN",
            "global_config",
            str(global_path if global_path.exists() else f"missing ({global_path})"),
        )
    )
    repo_path = repo_config_path(repo_root)
    diagnostics.append(
        Diagnostic(
            "OK" if repo_path.exists() else "WARN",
            "repo_config",
            str(repo_path if repo_path.exists() else f"missing ({repo_path})"),
        )
    )
    diagnostics.append(
        Diagnostic(
            "OK" if config.endpoint else "ERROR",
            "endpoint_configured",
            config.endpoint or "missing",
        )
    )
    inferred_org = config.organization or snapshot.organization
    inferred_repo = config.repository or snapshot.repository
    diagnostics.append(
        Diagnostic(
            "OK" if inferred_org and inferred_repo else "WARN",
            "repository_identity",
            f"organization={inferred_org} repository={inferred_repo}",
        )
    )
    diagnostics.append(Diagnostic("OK", "privacy_mode", config.privacy_mode.value))
    if config.privacy_mode == PrivacyMode.STRICT and not config.privacy_salt:
        diagnostics.append(
            Diagnostic(
                "ERROR",
                "privacy_salt",
                "strict mode requires a local privacy_salt",
            )
        )
    else:
        diagnostics.append(Diagnostic("OK", "privacy_salt", "configured or not required"))

    for hook_name in HOOK_TRIGGERS:
        installed = hook_installed(repo_root, hook_name)
        diagnostics.append(
            Diagnostic(
                "OK" if installed else "WARN",
                f"hook_{hook_name}",
                "installed" if installed else "not installed",
            )
        )

    claude_path = claude_settings_path(repo_root)
    if claude_path.exists():
        installed = claude_hooks_installed(repo_root)
        diagnostics.append(
            Diagnostic(
                "OK" if installed else "WARN",
                "claude_hooks",
                "installed" if installed else "not installed",
            )
        )
    else:
        diagnostics.append(Diagnostic("WARN", "claude_hooks", "Claude config not present"))

    diagnostics.append(Diagnostic("OK", "schema_version", str(SCHEMA_VERSION)))
    health = check_health(config)
    if health.ok:
        diagnostics.append(Diagnostic("OK", "endpoint_reachable", str(health.status_code)))
        if config.api_key:
            diagnostics.append(Diagnostic("OK", "auth", "configured and accepted by /health"))
        else:
            diagnostics.append(Diagnostic("WARN", "auth", "ENGOBS_API_KEY not configured"))
        payload = health.payload or {}
        supported = payload.get("supported_schema_versions")
        if isinstance(supported, list) and SCHEMA_VERSION not in supported:
            diagnostics.append(
                Diagnostic(
                    "WARN",
                    "schema_compatibility",
                    f"schema {SCHEMA_VERSION} not in {supported}",
                )
            )
        else:
            diagnostics.append(
                Diagnostic(
                    "OK",
                    "schema_compatibility",
                    "compatible or not advertised",
                )
            )
    else:
        if health.status_code == 401:
            diagnostics.append(Diagnostic("ERROR", "auth", "endpoint rejected credentials"))
        else:
            diagnostics.append(Diagnostic("WARN", "endpoint_reachable", health.message))
            diagnostics.append(Diagnostic("WARN", "auth", "could not verify auth"))
            diagnostics.append(
                Diagnostic("WARN", "schema_compatibility", "could not verify /health")
            )

    if not config.verify_tls:
        diagnostics.append(Diagnostic("WARN", "verify_tls", "TLS verification disabled"))
    else:
        diagnostics.append(Diagnostic("OK", "verify_tls", config.ca_bundle or "system trust store"))

    exit_code = 1 if any(item.status == "ERROR" for item in diagnostics) else 0
    if emit_output:
        for item in diagnostics:
            print(f"{item.status} {item.name}: {item.detail}")
    return exit_code, diagnostics
