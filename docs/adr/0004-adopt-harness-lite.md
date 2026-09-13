# ADR-0004: Adopt a Harness Lite for agent-assisted development

- **Status:** Accepted
- **Date:** 2026-09-12
- **Deciders:** Marcos Soto (maintainer)
- **Related:** `AGENTS.md`, `CLAUDE.md`, `.github/architecture.md`, `.github/standards.md`,
  `memory/`, `.claude/`, reference template `ml-python-base`

## Context

The repo had no agent-facing governance: no `AGENTS.md`/`CLAUDE.md`, no memory, no ADRs, and a
quality gate that did not enforce formatting or security lint. Agents entering the repo had to
rediscover the product, its privacy boundaries, and the definition of done every session. The
`ml-python-base` template offers a complete harness (projection engine, 25 skills, 6-agent
fleet, release lifecycle), which is far heavier than a ~2k-line CLI warrants.

## Decision

We will adopt a **Harness Lite**: *small context · strong boundaries · automatic verification ·
durable learning*. One canonical, always-loaded file (`AGENTS.md`) carries boundaries, the
working loop, the gate, the debugging protocol, and the ADR/memory rules; `CLAUDE.md` imports
it. Supporting pieces are kept minimal and tool-native.

Classification of the reference template's ideas:

| Idea | Verdict | Why |
| --- | --- | --- |
| Ground -> Plan -> Delegate -> Verify -> Compound loop, ceremony scaled by task size | ADOPT | Core behavior; the table prevents over-ceremony on tiny changes. Delegate is optional here. |
| 7-step debugging protocol inline in the agent file | ADOPT | Proven anti-thrash discipline; rules behind skill pointers are ignored by weaker models. |
| "Done = executed verification command, reported" | ADOPT | Single most valuable rule; `make check` already exists. |
| First-pass discipline (read governance + memory once, 1-3 sentence plan before editing) | ADOPT | Cheap; reduces rework. |
| Git-actions policy + tool-level `permissions.ask` on git mutations | ADOPT | Maintainer commits; enforced for Claude Code, textual for other tools. |
| `memory/` with dated one-fact entries | ADOPT (no `patterns.md`) | Conventions are few and live in `AGENTS.md`. |
| ADRs with template, numbering, trigger criteria | ADOPT | Seeded with real existing decisions. |
| SessionStart / Stop nudge hooks; `/plan` `/verify` `/retro` `/adr`; PR template | ADOPT (trimmed) | Tiny, non-blocking, tool-native. |
| Six governance files (`architecture`, `standards`, `domain-boundaries`, `sdlc`, `automation`, `orchestration`) | ADAPT -> 2 files | Boundaries live inline in `AGENTS.md`; mechanics in `standards.md`; structure in `architecture.md`. |
| Skills `systematic_debugging`, `verify_changes`, `retrospective`, `plan_and_execute_feature`, `brainstorm_quick`, `requesting-code-review` | ADAPT -> inline sections / commands | Each collapses to a few lines; Claude Code's built-in `/code-review` covers review. |
| `docs/agentic-workflow.md` | ADAPT -> `docs/development.md` | Human-facing setup + harness overview. |
| Docs-coverage CI gate | ADAPT -> checklist rule | A hard gate blocks refactor/test-only PRs in a small repo. |
| Read-only CI, single gate, declared dependencies | ADAPT | Already true; gate tightened with `ruff format --check` and `ruff S`. |
| Projection engine, adapters, registry, skills lock, `check-sync` | SKIP | Single canonical file + `@AGENTS.md` import removes the drift problem. |
| Agent fleet, orchestrator, handoff contract, checkpoint/resume | SKIP | No parallel fleet needed. |
| 25-skill tree, vendored skills, model tiers, release lifecycle, template sync, routing evals, OpenCode plugin, bandit | SKIP | Template-specific; ruff `S` replaces bandit at zero dependency cost. |

## Consequences

- Every session starts with ~130 lines of always-loaded context instead of none; everything
  else is on demand.
- `make check` is stricter (format + security lint); ruff is pinned to one minor so formatter
  output is deterministic between pre-commit, local, and CI.
- `tests/test_harness.py` fails if governance files, the ADR index, or hook scripts drift.
- Knowledge compounds through `memory/` and ADRs; the cost is a short retro at the end of
  substantive sessions.
- No projection tooling to maintain; if a second tool needs different instructions, add a
  thin wrapper file that imports or points to `AGENTS.md`.

## Alternatives considered

- **Copy `ml-python-base` wholesale** — dozens of files and a sync engine for a 2k-line CLI;
  context cost and maintenance outweigh the benefit.
- **Nothing beyond a README section** — not loaded automatically by agents; boundaries
  would keep being rediscovered or violated.
