# Security Policy

## Data collected

`engobs` collects only closed-schema telemetry metadata such as timestamps, aggregate Git counts, verification outcomes, selected AI tool name, and opaque session identifiers.

## Data not collected

The client does **not** collect source code, diffs, file names, file paths, prompts, completions, chat history, developer identity, remote URLs, terminal output, or environment dumps.

## Threat model

The main threat model is accidental collection of engineering content or personal identity. The kit mitigates this by using strict typed schemas, explicit forbidden-field validation, strict-mode pseudonymization, short-lived best-effort requests, and zero content persistence in local state.

## Privacy modes

- `standard`: explicit repo/project/branch identity, still no content or identity.
- `strict`: stable salted pseudonyms for identifiers; the salt stays local and is never transmitted.

## Secret handling

`ENGOBS_API_KEY` and `ENGOBS_PRIVACY_SALT` should preferably be provided via environment variables. If persisted in global config, the file is written with `0600` permissions on Unix.

## Responsible disclosure

Please report vulnerabilities privately to the repository owner before public disclosure.
