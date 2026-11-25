---
name: icp
description: Define the ideal customer profile - 11 fixed parameters (offer, outcome, industries, company size, regions, customer type, deal size, triggers, disqualifiers, proof, alternatives). Fills what it can from your website, then asks exactly 5 numbered clarifying questions. Writes directives/icp.md.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py *) Read Edit
---

# ICP: who we sell to

## 1. Gather evidence first
- If `.tmp/sites/<their domain>/pages.json` does not exist, ask for the domain and run the
  `read-website` skill first. Optional extras the user can give: their LinkedIn profile,
  2-3 best customers, a pitch deck.
- Read `pages.json` (and `facts.json`). For each of the 11 parameters in
  `directives/icp.md`, fill **value**, **source** (the page URL) and **confidence**:
  `✅ found` (stated on a page or by the user), `🟡 inferred` (your reasonable reading),
  `⬜ missing`. Keep the page readable: short values, no line breaks inside a cell, the
  parameter names bold as they are.
  Typical: offer, outcome, proof and industries are on the site; deal size, triggers and
  disqualifiers almost never are.

## 2. Ask exactly 5 clarifying questions
Pick the 5 most valuable: all `missing` first, then the weakest `inferred`. Write them as
a **plain numbered list** in one message (no multiple-choice menus). Each question:
- one line, in simple words;
- includes your current guess when you have one, so the answer can be "yes":
  `2. Company size: your case studies are all 20-100 person firms. Is that your sweet spot?`

End with: "Answer like `1 ... 2 ... 3 ...`. One line each is enough; 'skip' is fine."
Then **wait** for the answers.

## 3. Write the playbook
- Update the tables in `directives/icp.md`. Answers get source `owner`, confidence `✅ found`.
  Skipped items stay `missing`; never invent them.
- Replace the example bullets under **Fit rule** with 3 to 5 checkable rules, e.g.
  "10-200 employees; B2B service firm; in the UK and Ireland; not a direct competitor".
- **Triggers** feed the signals: each trigger is a candidate signal for the `signal-builder`
  skill; hiring-related ones ("they hire X") go straight into the map in
  `directives/signals/hiring.md`.
- Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py profile-check icp` and show the result.
- Show the final table to the user. Next: `persona`.
