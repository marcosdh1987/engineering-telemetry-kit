# AGENTS.md — engineering-telemetry-kit

Canonical instructions for any coding agent (Claude Code, Codex, OpenCode, Copilot, humans).
`CLAUDE.md` imports this file. Keep it short: everything here is loaded on every session.

## 1. What this is

`engobs` is a small, portable, privacy-first CLI that emits **Engineering Delivery telemetry**
(schema v4) from Git hooks, Claude Code hooks and `engobs verify` to a configurable gateway.
It measures the engineering *process* without observing engineering *content*.
Runtime: Python >= 3.11, stdlib `urllib` transport, `pydantic` is the only runtime dependency.

Documentation ownership: this repo owns "how to instrument a repository"; the `ai-gateway`
repo owns "how to operate the backend/control plane". Do not duplicate backend docs here.

## 2. Inviolable boundaries

Never weaken these. If a task seems to require it, stop and explain before editing.

- **Never collect or send content or identity**: source code, diffs, patches, filenames, paths,
  prompts, completions, transcripts, terminal output, developer name/email/username, remote
  URLs, environment dumps, secrets. `src/engobs/privacy/validation.py` (`FORBIDDEN_KEYS`) is the
  executable list; every outbound event passes `validate_no_forbidden_fields` twice.
- **Closed schema**: `TelemetryEvent` keeps `extra="forbid"`. A new field needs an ADR and a
  `FORBIDDEN_KEYS` review; bumping `SCHEMA_VERSION` is a backend-coordinated decision. The
  wire shape is owned by the collector (`ai-gateway`); change `domain/wire.py` and
  `tests/test_wire.py` together.
- **Strict mode**: `STRICT_FIELDS` are pseudonymized with a local `privacy_salt` that is never
  transmitted, logged, or written into the repository.
- **Secrets**: `api_key` and `privacy_salt` never appear in logs, test output, `.engobs.toml`,
  or committed files. Redact before logging.
- **Non-blocking**: telemetry must never block or fail engineering work. Hooks stay `|| true`,
  HTTP has a short timeout (1.5 s default), transport errors are logged and swallowed.
- **Config precedence is fixed**: `CLI > env > repo profile > repo > global profile > global >
  defaults` (`src/engobs/config/loader.py`). Do not reorder it.
- **Managed blocks only**: `engobs install/uninstall` edit only the delimited engobs block in
  Git hooks and only engobs-managed entries in `.claude/settings.json`. Never clobber user
  hooks or settings.
- **No new runtime dependencies** without an ADR (portability is a feature).

## 3. Repo map

- `src/engobs/cli.py` — argparse entry point (`engobs`), dispatches to `commands/`.
- `src/engobs/commands/` — `install`, `uninstall`, `doctor`, `snapshot`, `verify`, `ai_session`.
- `src/engobs/config/` — `models.py` (pydantic, `extra="forbid"`), `loader.py` (precedence, env map).
- `src/engobs/domain/` — `events.py` (flat `TelemetryEvent`), `wire.py` (collector schema v4
  envelope + `attributes`, UUID5 work units; ADR-0005), `fingerprint.py`.
- `src/engobs/privacy/` — forbidden-field validation, strict-mode pseudonymization.
- `src/engobs/transport/http.py` — urllib POST/GET, `send_event`, `check_health`.
- `src/engobs/git/` — snapshot aggregates (`context.py`), managed hook blocks (`hooks.py`).
- `src/engobs/ai/claude.py` — managed Claude Code hook entries. `state/store.py` — `.git/engobs/state.json`.
- `tests/` — pytest; HTTP is mocked at `http_transport.request.urlopen`, git via temp repos.
- `docs/` — user docs. `docs/adr/` — decisions. `memory/` — durable working memory.

## 4. Working loop: Ground -> Plan -> (Delegate) -> Verify -> Compound

| Task size | Ceremony |
| --- | --- |
| Tiny (typo, one-line fix, doc wording) | Read the file, smallest safe change, run the narrowest check. No ADR/memory unless something non-obvious was learned. |
| Normal (bug fix, small feature) | Full loop below. Focused tests first, `make check` to close. |
| Large or risky (schema, transport, privacy, config precedence) | Full loop + written plan agreed with the user + ADR. |

1. **Ground.** Read this file, `memory/context.md` and `memory/learnings.md` once. Read the code
   you will change and the tests that exercise it. Blind edits are the most expensive failure.
2. **Plan.** Before the first edit write 1-3 sentences: intent or root cause, files/symbols to
   touch, and the exact verification command. Re-read governance only if the plan changes;
   repeated reads without a plan update are a thrash signal.
3. **Delegate** (optional). Parallelize only genuinely independent read-only exploration.
4. **Verify.** Run the focused test after each substantive change; close with `make check`.
5. **Compound.** Persist non-obvious learnings in `memory/learnings.md`; write an ADR for
   hard-to-reverse decisions; update `docs/` when behavior changes.

## 5. Quality gate and definition of done

- Gate: `make check` = `ruff format --check` + `ruff check` (incl. security rules `S`) +
  `mypy src` (strict) + `pytest` + `python -m build`. CI runs exactly this and is read-only.
- Local setup: `uv venv .venv && uv pip install -e ".[dev]"` then `source .venv/bin/activate`.
- **A completion claim without an executed verification command is a defect.** Report the
  exact commands you ran and their results; if a gate fails or a step was skipped, say so.
- Behavior changes ship with tests and a `docs/` update in the same change.
- Do not `pip install` ad hoc; declare dependencies in `pyproject.toml`.

## 6. Debugging protocol (follow inline, do not delegate)

1. Pin the working root (`pwd`, `ls`) and prefix every path with it.
2. Open the evidence: the failing test and the implementation it exercises.
3. Restate the failure in 1-2 lines: exception type, message, operands, `file:line`. No fix before this.
4. Reproduce with the repo's own runner (`pytest tests/test_x.py -k name`). Never a synthetic script.
5. One hypothesis at a time. After two probes that fail to confirm, stop, re-read, reframe.
6. Failed edit -> smaller edit. Re-read the ~10 lines around the target; never retry the same patch.
7. Close only on a green rerun of the exact step-4 command, then `make check`.

## 7. Decisions and memory

- **ADR** (`docs/adr/`, use `/adr` or copy `0000-template.md`) when a decision is hard to
  reverse: new dependency, schema/event field, privacy or transport boundary, config
  semantics, a convention everyone must follow.
- **Memory** (`memory/learnings.md`) for durable, non-obvious facts: gotchas, dead ends,
  why-it-is-this-way. One dated fact per entry with *Why it matters* / *How to apply*.
  Skip anything obvious from code, README or git history.
- Update `memory/context.md` (active focus, open threads) when the focus shifts or at session end.

## 8. Git and scope rules

- **Never run `git commit`, `git push`, `git merge`, `git rebase`.** Leave changes unstaged;
  the maintainer commits. Suggest a commit message as text if useful.
- Edit, never rewrite whole files. One root cause per change. Minimal, related diff only.
- Stay in scope: if an out-of-scope change seems necessary, explain first, then decide.
- Code, comments, docs and commit messages in English; converse in the user's language.

## 9. Review checklist (before "ready")

Gate green and pasted · boundaries in section 2 untouched · no unrelated churn · tests verify
behavior, not mocks · docs updated · findings triaged Critical / Important / Minor with `file:line`.

## 10. Pointers

`.github/architecture.md` (data flow, dependency direction, extension points) ·
`.github/standards.md` (tooling, style, test conventions, retry policy) ·
`docs/development.md` (human setup guide) · `docs/adr/README.md` · `memory/README.md`.
