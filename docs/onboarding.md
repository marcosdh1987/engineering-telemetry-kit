# Onboarding: instrument an existing repository

Step-by-step guide to point a Git repository at an Engineering Gateway with `engobs`. This is
the flow validated on a real deployment (HTTPS gateway behind Cloudflare + a reverse proxy).
Operating the backend itself (collector, storage, dashboards, LiteLLM, auth) is documented in
the `ai-gateway` repository.

## Prerequisites

- An Engineering Gateway reachable over HTTPS; `GET /health` returns 200.
- A Git repository (with a remote if you want organization/repository inferred).
- `uv` (or `pipx`) to install the CLI. Python is only needed to run `engobs` itself.
- Optional: a LiteLLM virtual key for the project (see "Correlating AI consumption").

## What engobs sends (and never sends)

`engobs` never sends source code, diffs, filenames, paths, prompts, completions, developer
identity (name, email, username), secrets, remote URLs, or terminal output. In `standard` mode
it sends repository, branch, commit SHAs, aggregate line/file counts, timestamps, verification
outcomes, the AI tool name and an opaque session id. In `strict` mode identifiers are
pseudonymized with a local salt that never leaves the machine. Details: `docs/privacy.md`.

## Step 1: verify the backend

```bash
curl -i https://telemetry.example.com/health
```

Expected: `200` with a JSON body such as `{"status": "ok", "schema_version": 4}`.

## Step 2: install the engobs CLI

Published package:

```bash
uv tool install engineering-telemetry-kit
```

Private GitHub repository:

```bash
uv tool install git+ssh://git@github.com/<org>/engineering-telemetry-kit.git
```

Verify: `engobs --help`. To upgrade later, add `--force` to the same command.

## Step 3: create `.engobs.toml` in the repository root

```toml
endpoint = "https://telemetry.example.com"

organization = "example-org"
project = "my-project"

privacy_mode = "standard"
verify_tls = true
```

- `endpoint` is the gateway base URL (no `/events` suffix).
- `repository` is inferred from the Git remote; set it explicitly only if there is no remote.
- Commit this file: it contains no secrets. API keys and privacy salts never go here (Step 10).
- Alternative for many repositories: a global profile in `~/.config/engobs/config.toml`, see
  `docs/enterprise-deployment.md`. Global config is optional.

## Step 4: install the hooks

```bash
engobs install
```

Installs `post-commit` / `post-checkout` wrappers (managed block, non-blocking) and, if the
repository uses Claude Code, managed hook groups in `.claude/settings.json`.

## Step 5: run the doctor

```bash
engobs doctor
```

Expected on a healthy setup:

```text
OK configuration_source: repo=.engobs.toml (profile=default)
OK repo_config: /path/to/repo/.engobs.toml
INFO global_config: not configured (optional)
OK endpoint_configured: https://telemetry.example.com
OK repository_identity: organization=example-org project=my-project repository=my-repo
OK privacy_mode: standard
OK privacy_salt: configured or not required
OK hook_post-commit: installed
OK hook_post-checkout: installed
OK claude_hooks: installed
OK schema_version: 4
OK endpoint_reachable: 200
WARN auth: ENGOBS_API_KEY not configured
OK schema_compatibility: compatible or not advertised
OK verify_tls: system trust store
```

- `INFO global_config: not configured (optional)` is normal with repo-level configuration.
- `WARN auth: ENGOBS_API_KEY not configured` is expected in a pilot where the backend does
  not require authentication (Step 10).
- `WARN claude_hooks: Claude config not present` is fine if the repo does not use Claude Code.
- `ERROR repository_identity` means organization, project or repository could not be
  resolved; the collector requires all three. Set them in `.engobs.toml` or add a Git remote.
- Any `WARN endpoint_reachable` comes with `HINT` lines; see `docs/troubleshooting.md`.

## Step 6: send a manual snapshot

```bash
engobs snapshot --trigger manual
```

No output means the event was accepted (`ENGOBS_DEBUG=true engobs snapshot --trigger manual`
shows `status=202` per event). `WARN telemetry not sent: HTTP 403 Forbidden` (or
similar) means the request was rejected on the way to the collector; run `engobs doctor`.

## Step 7: AI tool hooks

Claude Code hooks are installed by Step 4 when `.claude/settings.json` exists or is created.
Close and reopen Claude Code (or start a new session) so the settings are reloaded. Each
session then emits `ai_session_started` / `ai_session_ended` plus a snapshot per turn.
See `docs/integrations/claude-code.md`.

## Step 8: optional verification wrapper

Wrap your test or check command to emit verification outcomes and durations:

```bash
engobs verify -- pytest
engobs verify -- make check
```

The wrapper returns the wrapped command's exit code; telemetry never changes it.

## Step 9: validate in the dashboard

After Steps 6-8, confirm in the gateway dashboard that the following appear for the project:
project and repository, branch, activity, aggregate LOC, a verification outcome, and an AI
session. If something is missing, the corresponding step above did not reach the backend.

## Step 10: authentication

**Pilot** (backend `auth_required=false`): nothing to configure. `engobs doctor` shows
`WARN auth: ENGOBS_API_KEY not configured`, which is expected.

**Production** (backend telemetry auth enabled): provide the key through the environment,
never in `.engobs.toml`:

```bash
export ENGOBS_API_KEY=...
engobs doctor   # OK auth: configured and accepted by /health
```

Managed workstations can also store it in `~/.config/engobs/config.toml` (written with
`0600` permissions). This key is the telemetry gateway key; it is **not** a LiteLLM virtual
key.

## Correlating AI consumption with Engineering Delivery

`engobs` and LiteLLM are independent: `engobs` reports delivery activity, LiteLLM reports
model usage. To join them in the gateway, use the same name on both sides:

```text
.engobs.toml           project = "msi-contract-monitoring-workspace"
LiteLLM virtual key    alias   = "msi-contract-monitoring-workspace"
```

Never put LiteLLM keys in `.engobs.toml`.

### Local Claude Code pointing at LiteLLM

A developer can route Claude Code through the LiteLLM gateway with a project-specific key.
Conceptually, in a **local, untracked** settings file:

```text
ANTHROPIC_BASE_URL = https://ai.example.com
ANTHROPIC_AUTH_TOKEN = <project LiteLLM virtual key>
```

Keep secrets out of Git: put them in `.claude/settings.local.json` (not `settings.json`) and
confirm it is ignored:

```bash
git check-ignore .claude/settings.local.json
```

If the command prints nothing, add `.claude/settings.local.json` to `.gitignore` first.

## Upgrading an already instrumented repository

Hooks call the `engobs` binary, so upgrading the CLI is enough; no reinstall of hooks needed:

```bash
uv tool install --force git+ssh://git@github.com/<org>/engineering-telemetry-kit.git
engobs doctor
engobs snapshot --trigger manual
```

Exception: repositories instrumented with engobs < 0.1.1 should run `engobs install` once
more so the Claude Code hook entries are migrated to the valid schema.
