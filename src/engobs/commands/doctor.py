from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engobs import SCHEMA_VERSION
from engobs.ai.claude import claude_hooks_installed, claude_settings_path
from engobs.commands.common import configure_logging, load_runtime_config
from engobs.config.loader import ConfigSources, describe_config_sources
from engobs.config.models import PrivacyMode
from engobs.git.context import GitError, get_snapshot
from engobs.git.hooks import HOOK_TRIGGERS, hook_installed
from engobs.transport.http import HealthResult, check_health

CLOUDFLARE_HINT = (
    "Cloudflare rejected the HTTP client signature. "
    "Verify the engobs User-Agent (upgrade engobs) or the Cloudflare security rules."
)
HTTP_HINTS: dict[int, str] = {
    401: "endpoint rejected credentials: set ENGOBS_API_KEY (or a profile api_key)",
    403: "a reverse proxy/CDN may be blocking the engobs client",
    404: "/health not found: check that the endpoint is the gateway base URL without a path",
}


@dataclass(frozen=True)
class Diagnostic:
    status: str
    name: str
    detail: str
    hints: tuple[str, ...] = ()


def http_hints(health: HealthResult) -> list[str]:
    """Actionable hints for a failed /health probe. Deliberately simple string checks."""
    hints: list[str] = []
    status = health.status_code
    if status is None:
        hints.append("connection failed: check network, DNS, proxy, and TLS (ENGOBS_CA_BUNDLE)")
    elif status in HTTP_HINTS:
        hints.append(HTTP_HINTS[status])
    elif status >= 500:
        hints.append("gateway error: the collector behind the proxy is unhealthy or unreachable")
    server = health.server or ""
    body = health.body_snippet or ""
    if "cloudflare" in server or "error code: 1010" in body:
        hints.append(CLOUDFLARE_HINT)
    return hints


def _emit(diagnostics: list[Diagnostic]) -> None:
    for item in diagnostics:
        print(f"{item.status} {item.name}: {item.detail}")
        for hint in item.hints:
            print(f"HINT {hint}")


def describe_sources(sources: ConfigSources, profile: str | None) -> str:
    parts: list[str] = []
    if sources.global_exists:
        parts.append(f"global={sources.global_path}")
    if sources.repo_exists:
        label = "repo overrides" if sources.global_exists else "repo"
        parts.append(f"{label}={sources.repo_path.name}")
    if sources.env_vars:
        parts.append("env=" + ",".join(sources.env_vars))
    if not parts:
        parts.append("defaults only")
    return f"{' '.join(parts)} (profile={profile or 'default'})"


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
            _emit(error_diagnostics)
        return 1, error_diagnostics

    config, repo_root = load_runtime_config(cwd, profile)
    configure_logging(config.debug)
    diagnostics: list[Diagnostic] = []

    sources = describe_config_sources(repo_root, profile_override=profile)
    diagnostics.append(
        Diagnostic("OK", "configuration_source", describe_sources(sources, config.profile))
    )
    # Neither file is required on its own: repo-level, global-profile, and env-only setups
    # are all valid, so a missing file is informational unless nothing configures an endpoint.
    diagnostics.append(
        Diagnostic(
            "OK" if sources.repo_exists else "INFO",
            "repo_config",
            str(sources.repo_path) if sources.repo_exists else "not present (optional)",
        )
    )
    diagnostics.append(
        Diagnostic(
            "OK" if sources.global_exists else "INFO",
            "global_config",
            str(sources.global_path) if sources.global_exists else "not configured (optional)",
        )
    )
    if sources.profile and not (sources.profile_in_global or sources.profile_in_repo):
        diagnostics.append(
            Diagnostic(
                "WARN",
                "profile",
                f"profile '{sources.profile}' selected but not defined in any config file",
            )
        )
    diagnostics.append(
        Diagnostic(
            "OK" if config.endpoint else "ERROR",
            "endpoint_configured",
            config.endpoint or "missing",
            ()
            if config.endpoint
            else (
                f"set ENGOBS_ENDPOINT, or add endpoint to .engobs.toml or {sources.global_path}",
            ),
        )
    )
    inferred_org = config.organization or snapshot.organization
    inferred_project = config.project or snapshot.project
    inferred_repo = config.repository or snapshot.repository
    identity_complete = bool(inferred_org and inferred_project and inferred_repo)
    # The collector requires all three dimensions; without them every event is rejected.
    diagnostics.append(
        Diagnostic(
            "OK" if identity_complete else "ERROR",
            "repository_identity",
            f"organization={inferred_org} project={inferred_project} repository={inferred_repo}",
            ()
            if identity_complete
            else (
                "set organization/project/repository in .engobs.toml "
                "(or ENGOBS_ORGANIZATION / ENGOBS_PROJECT / ENGOBS_REPOSITORY), "
                "or add a git remote so they can be inferred",
            ),
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
        hints = tuple(http_hints(health))
        if health.status_code == 401:
            diagnostics.append(Diagnostic("OK", "endpoint_reachable", health.message))
            diagnostics.append(Diagnostic("ERROR", "auth", "endpoint rejected credentials", hints))
        else:
            diagnostics.append(Diagnostic("WARN", "endpoint_reachable", health.message, hints))
            diagnostics.append(Diagnostic("WARN", "auth", "could not verify auth"))
        diagnostics.append(Diagnostic("WARN", "schema_compatibility", "could not verify /health"))

    if not config.verify_tls:
        diagnostics.append(Diagnostic("WARN", "verify_tls", "TLS verification disabled"))
    else:
        diagnostics.append(Diagnostic("OK", "verify_tls", config.ca_bundle or "system trust store"))

    exit_code = 1 if any(item.status == "ERROR" for item in diagnostics) else 0
    if emit_output:
        _emit(diagnostics)
    return exit_code, diagnostics
