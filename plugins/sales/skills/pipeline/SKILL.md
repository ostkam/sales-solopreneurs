---
name: pipeline
description: Daily what-to-do-now view from the local database - replies to answer, accepted invites without a follow-up DM, drafts ready to send, new signals, fit accounts without people, stale invites, old signals to re-check. Also opens the live local view (dashboard) of accounts, contacts and signals in the browser. Use for what should I do today, show my pipeline, open/start the CRM, open the dashboard, show my data.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read
---

# Pipeline: what to do today

**Live view (dashboard):** when the user wants to *see* the data, run
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py ui` **in the background** (it keeps running
and opens the browser; it moves to the next free port if 8765 is taken). It shows Today,
Accounts, Contacts and Signals, refreshes every few seconds, and is read-only: every change
still goes through `gtm.py` with a dry run. Tell the user the URL it printed. If it is
already running, just give the URL again.

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py pipeline` (the same list is the **Today**
   tab of the live view; `--html .tmp/pipeline.html` writes a static copy to share).
2. Turn it into a short plan, highest value first:
   1. answer replies (always first);
   2. follow-up DMs for accepted invites (`linkedin` skill);
   3. send ready drafts;
   4. find 1-2 people for new fit accounts (`import-leads`);
   5. withdraw invites open > 3 weeks, or try email instead;
   6. re-check old signals: still live? `gtm.py close-signal --id N --commit` if gone.
3. Ask the user what was sent since last time and log it (`log-touch`), so tomorrow's view
   is right. Numbers worth tracking weekly: invites sent, accepted %, DMs sent, replies,
   meetings. Acceptance is not the goal; replies and meetings are.
