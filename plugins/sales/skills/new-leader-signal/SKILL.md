---
name: new-leader-signal
description: Find people who started a relevant role in the last 90 days (new leaders change suppliers and tools early) from a pasted Sales Navigator or LinkedIn search, check their companies against the ICP, and store the change as a signal.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write Agent
---

# New leader signal

1. Search help for the user: in Sales Navigator, Lead filters: the persona's titles
   (from `directives/personas.md`), "Changed jobs in past 90 days", the ICP regions and
   company headcount. Copy result pages and paste them.
2. From the paste, extract: person, title, company, time in role (keep only < 6 months).
3. Companies not in the DB: research them like `research-accounts` (subagents, fit rule),
   with a signal line per person:
   `"signal": {"type": "new_leader", "detail": "<name>, <title>, <n> months in role", "observed_at": "YYYY-MM-DD"}`
4. `apply-research` (dry run, then `--commit`), then import the people with `import-leads`.
5. The note: never "congrats on the new role" from a stranger. Write about their work or
   background, as in `directives/linkedin.md`.
