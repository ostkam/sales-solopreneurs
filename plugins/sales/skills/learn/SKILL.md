---
name: learn
description: Close the loop - read the results (accept rates, replies, meetings, research rejections) from the database and the playbooks' learnings, find what works and what does not, and propose concrete changes to the ICP, personas, signals and message rules.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Edit
---

# Learn: make the system better

1. Pull the numbers (read-only):
   - acceptance by note style and persona: touches `invite` vs `accepted` per contact persona;
   - replies by channel, signal type and account segment;
   - research verdicts: top reasons for `no` (from `verdicts`);
   - signals: yield per source (ads pasted vs fits, from the Learnings lines).
2. Read every **Learnings** section in `directives/`.
3. Write 3-5 findings, each with the evidence ("12 invites with a post-based note, 7
   accepted; 10 with a career-based note, 2 accepted"). Small samples: say so; under ~20
   sends a difference is a hint, not a result.
4. Propose concrete edits (an ICP size change, a new disqualifier, a persona to drop, a
   banned word, a signal to stop). Apply only the ones the user approves, each with a
   dated Learnings line.
5. Suggest one experiment for next week (e.g. two note styles, 15 people each).
