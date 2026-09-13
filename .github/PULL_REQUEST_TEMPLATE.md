## What changed

<!-- One or two sentences. -->

## Why

<!-- The problem being solved. Link the issue, ADR, or memory entry if there is one. -->

## Verification

<!-- What did you actually run? Paste the result, not the intention. -->

- [ ] `make check` passes locally (format, ruff incl. S, mypy strict, pytest, build)
- [ ] Behavior changes ship with tests and a `docs/` update

## Privacy impact

- [ ] No new event field, or: ADR linked and `FORBIDDEN_KEYS` / `STRICT_FIELDS` reviewed
- [ ] No secret (`api_key`, `privacy_salt`) can reach logs, payloads, or committed files

## Notes for the reviewer

<!-- Trade-offs, open questions, follow-ups deliberately left out. -->
