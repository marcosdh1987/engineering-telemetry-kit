#!/usr/bin/env bash
# SessionStart nudge (non-blocking). Stdout is added to the session context. Always exits 0.
set -euo pipefail

cat <<'MSG'
[engobs] Loop: Ground -> Plan -> Verify -> Compound (AGENTS.md).
- Read memory/context.md and memory/learnings.md before editing.
- Boundaries (AGENTS.md section 2): never send content/identity/secrets; telemetry never blocks.
- Gate: make check (/verify). Decisions: /adr. Learnings: /retro. Never git commit.
MSG

exit 0
