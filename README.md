# engineering-telemetry-kit

`engineering-telemetry-kit` provides the `engobs` CLI: a lightweight, portable, privacy-first
emitter of Engineering Delivery telemetry (schema v4) for any Git repository.

- installs safe, non-blocking Git hooks and Claude Code hooks
- captures aggregate Git, verification, and AI-session metadata
- sends it to a configurable Engineering Gateway, also behind Cloudflare / reverse proxies
- never collects source code, diffs, filenames, paths, prompts, completions, developer
  identity, secrets, remote URLs, or terminal output

## Quickstart

```bash
uv tool install engineering-telemetry-kit          # or: uv tool install git+ssh://git@github.com/<org>/engineering-telemetry-kit.git
cd my-repo
cat > .engobs.toml <<'TOML'
endpoint = "https://telemetry.example.com"
organization = "example-org"
project = "my-project"
TOML
engobs install
engobs doctor
engobs snapshot --trigger manual
```

Full walkthrough, expected `doctor` output, authentication and LiteLLM correlation:
**[docs/onboarding.md](docs/onboarding.md)**.

## Core commands

```bash
engobs install                      # Git + Claude Code hooks (idempotent)
engobs doctor                       # configuration, hooks, endpoint, auth, schema (with HINTs)
engobs snapshot --trigger manual    # send a branch snapshot now
engobs verify -- pytest             # wrap a check and report its outcome
engobs ai-session start --tool claude   # session id from hook stdin, or --session-id
engobs uninstall
```

## Privacy modes

- `standard`: explicit repository/branch/commit identity and aggregate counts; never content
  or personal identity.
- `strict`: additionally pseudonymizes repository, branch, project, organization, commit and
  session identifiers with a local salt that is never transmitted.

## Documentation

- [Onboarding](docs/onboarding.md) — instrument an existing repository (the validated flow)
- [Troubleshooting](docs/troubleshooting.md) — 403 behind Cloudflare, 422 on empty POST, reverse proxy setup, auth
- [Privacy model](docs/privacy.md)
- [Enterprise deployment](docs/enterprise-deployment.md) — repo-level vs global profiles, TLS, rollout
- [AI Gateway integration](docs/integrations/ai-gateway.md) · [Claude Code](docs/integrations/claude-code.md) · [Git hooks](docs/integrations/git-hooks.md)
- [Development guide](docs/development.md) — quality gate and the agent harness (`AGENTS.md`)
- [Changelog](CHANGELOG.md)

Backend operation (collector, storage, dashboards, LiteLLM, auth) lives in the `ai-gateway`
repository.
