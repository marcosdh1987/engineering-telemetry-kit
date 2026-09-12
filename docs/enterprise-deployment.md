# Enterprise deployment

## Profiles

Use reusable profiles in `~/.config/engobs/config.toml`:

```toml
[profiles.company]
endpoint = "https://engineering.company.internal"
privacy_mode = "strict"
verify_tls = true
ca_bundle = "/etc/company/ca.pem"
```

Select them with `ENGOBS_PROFILE=company` or `engobs --profile company doctor`.

## Repository override

Per-repo overrides live in `.engobs.toml` at the root of a target repository, for example:

```toml
profile = "company"
project = "payments-platform"
organization = "client-a"
```

Do not store secrets there.

## TLS and company CA

TLS verification is on by default. Enterprises can provide `ENGOBS_CA_BUNDLE=/path/company-ca.pem`. Setting `ENGOBS_VERIFY_TLS=false` is supported but surfaced as a visible warning by `engobs doctor`.

## Rollout patterns

- bootstrap via MDM or workstation provisioning
- run `engobs install` during repo template bootstrap
- inject API keys and profile selection through shell profile, CI, or secret managers
- use the same CLI for personal, company, and client gateways without reinstalling
