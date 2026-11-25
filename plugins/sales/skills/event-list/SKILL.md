---
name: event-list
description: Score a conference or event list (attendees, exhibitors, speakers) against the ICP and personas, research the organisations that might fit, and store them with the event as a signal and a shared-context first line.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write Agent
---

# Event list

1. The user drops the export (CSV) or pastes the exhibitor/attendee page into `input/`.
2. Pre-filter by rules first: titles that match a persona, organisations not in the
   disqualifiers. Watch for word traps (e.g. "cto" inside "doctoral"; match whole words).
3. **Research by organisation, not by person**: group people by company, then run
   `account-researcher` subagents on the companies (fit rule from `directives/icp.md`),
   with `"signal": {"type": "event", "detail": "<event name> <exhibitor/attendee/speaker>"}`.
4. `apply-research` dry run, then `--commit`; import the matching people with `import-leads`.
5. First line idea for notes and emails: the shared event ("saw you are exhibiting at X").
   Before the event: ask to meet at the booth. After: refer to a talk or a stand only if true.
