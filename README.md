# engineering-telemetry-kit

`engineering-telemetry-kit` provides the `engobs` CLI: a lightweight, portable, privacy-first emitter for Engineering Delivery telemetry.

## What it does

- installs safe Git hooks in any Git repository
- captures aggregate Git, verification, and AI-session metadata
- emits schema v4 telemetry to a configurable Engineering Gateway
- supports reusable global config, per-repo overrides, and multi-profile usage

## What it does **not** collect

- source code, diffs, patches, filenames, or file paths
- prompts, completions, chat transcripts, or terminal output
- developer identity such as name, email, username, or employee ID
- secrets, API keys, passwords, remote URLs, or environment dumps

## Quickstart

### Personal

```bash
uv tool install engineering-telemetry-kit
export ENGOBS_ENDPOINT=http://192.168.x.x:8090
export ENGOBS_API_KEY=your-key
cd my-repo
engobs install
engobs doctor
```

### Company

```bash
export ENGOBS_PROFILE=company
engobs install
engobs doctor
```

Example global config:

```toml
[profiles.company]
endpoint = "https://engineering.company.internal"
privacy_mode = "strict"
verify_tls = true
ca_bundle = "/etc/company/ca.pem"
```

## Core commands

```bash
engobs install
engobs doctor
engobs snapshot --trigger manual
engobs verify -- pytest
engobs ai-session start --tool claude --session-id opaque-id
engobs uninstall
```

## Privacy modes

- `standard`: sends explicit repository and branch identity, never content or personal identity.
- `strict`: pseudonymizes repository, branch, project, organization, and commit identifiers with a local salt that is never transmitted.

## Architecture

```text
Repository
   +-> Git hooks
   +-> Claude hooks
   +-> engobs verify
          |
          v
       engobs CLI
          |
          v
  Configurable Engineering Gateway
```

## Documentation

- `docs/development.md` — contributing, quality gate, and the agent harness (`AGENTS.md`)
- `docs/privacy.md`
- `docs/enterprise-deployment.md`
- `docs/agent-integration.md`
- `docs/integrations/ai-gateway.md`
- `docs/integrations/claude-code.md`
- `docs/integrations/git-hooks.md`
