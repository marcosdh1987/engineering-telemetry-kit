# Enterprise deployment

`engobs` supports two configuration styles. Both are complete on their own; they can also be
combined (global profile + per-repo overrides). Precedence is always
`CLI > env > repo profile > repo > global profile > global > defaults`.

## Option A: repo-level configuration

Each repository contains a committed `.engobs.toml`:

```toml
endpoint = "https://telemetry.example.com"
organization = "client-a"
project = "payments-platform"
privacy_mode = "standard"
```

Ideal for pilots, client projects, and anything that benefits from explicit per-project
configuration living next to the code. No global file is needed; `engobs doctor` reports
`INFO global_config: not configured (optional)`, which is not an error.

## Option B: global profile

A per-user file, optionally provisioned by MDM or a workstation bootstrap script:

```toml
# ~/.config/engobs/config.toml  (or $XDG_CONFIG_HOME/engobs/config.toml)
[profiles.company]
endpoint = "https://engineering.company.internal"
privacy_mode = "strict"
verify_tls = true
ca_bundle = "/etc/company/ca.pem"
```

Select it with `ENGOBS_PROFILE=company`, `engobs --profile company doctor`, or per repo:

```toml
# .engobs.toml
profile = "company"
project = "payments-platform"
organization = "client-a"
```

Ideal for many repositories, managed workstations, and centralized rollout: the endpoint,
privacy mode and CA bundle are defined once. `engobs doctor` shows what applies:

```text
OK configuration_source: global=/home/dev/.config/engobs/config.toml repo overrides=.engobs.toml (profile=company)
```

## Secrets

`ENGOBS_API_KEY` and `ENGOBS_PRIVACY_SALT` should be provided through the environment (shell
profile, CI, secret manager). If persisted, they belong in the global config, which `engobs`
writes with `0600` permissions; never in `.engobs.toml`. In strict mode `engobs install`
generates and stores the salt in the global config when none exists.

## TLS and company CA

TLS verification is on by default. Provide a private CA with `ENGOBS_CA_BUNDLE=/path/ca.pem`
or `ca_bundle` in a profile. `ENGOBS_VERIFY_TLS=false` is supported but surfaced as a visible
warning by `engobs doctor`.

## Network

Every request identifies itself as `User-Agent: engobs/<version>` so proxies, WAFs and CDNs
can allow-list the client. Expose the collector only through an HTTPS reverse proxy; see
`docs/troubleshooting.md` for the recommended topology and known CDN issues.

## Rollout patterns

- bootstrap the global profile via MDM or workstation provisioning
- run `engobs install` during repo template bootstrap; hooks call `engobs` from `PATH`, so
  upgrading the CLI (`uv tool install --force ...`) upgrades every instrumented repo
- inject API keys and profile selection through shell profile, CI, or secret managers
- use the same CLI for personal, company, and client gateways without reinstalling
