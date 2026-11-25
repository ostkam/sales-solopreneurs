---
name: discovery-call
description: Prepare and debrief a discovery or customer interview the Mom Test way - questions about their real past behaviour, not opinions about your idea - from the account's data, then write what you learned back into the ICP and personas.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Edit
---

# Discovery call

## Before
Read the account and person (`gtm.py query ...`), its signals and its website (`.tmp/sites/<domain>/`). Write a one-page prep:
- 1 warm-up question about their role and priorities.
- 6-8 questions about **specific past events**: "Walk me through the last time ...",
  "What did you try? What did it cost?", "Who decided?", "What happened next?".
  Built on the persona's pains, never "would you use...?" or "is this a good idea?".
- What NOT to do: pitch early (friends and polite people give compliments, not data).
- The close: ask for one commitment: time (a next meeting), reputation (an introduction),
  or data (examples you can use). "Sounds great, send me info" is a no.

## After
The user pastes notes. Extract: their exact words for the pain, what they tried, budget
and decision process, objections, the commitment (or none). Then:
- update `directives/personas.md` (pains in their words, objections) and the ICP
  `triggers`/`alternatives`, with source "call <date>";
- `gtm.py log-touch --channel other --kind meeting --outcome <commitment or none> --commit`;
- one row in the Learnings table in `directives/icp.md`.
