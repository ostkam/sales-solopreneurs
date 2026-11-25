---
name: research-accounts
description: Check a list of companies against the ICP fit rule with parallel research subagents - each company gets fit yes/no/unknown with a reason from its own website - then validate and store. Use after importing accounts from any list.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py *) Read Write Agent
---

# Research accounts

1. Get the list: `gtm.py query "select name, domain, size_employees, country from accounts where fit='unknown' and status!='disqualified'"`
   (or the user's CSV). Skip rows without a domain or LinkedIn URL; report them.
2. Split into batches of 5-8. Start one `account-researcher` subagent per batch, in
   parallel (max 4 at once). Give each: its rows, the **Fit rule** and the full table from
   `directives/icp.md`, and its output file `.tmp/research/<date>_fit_<batch>.jsonl`.
3. Each line: `{"company","domain","fit","reason","country","size_employees","industry","description","linkedin_url"}`.
   `description` = what they sell and to whom, in 1-2 sentences (this enriches the account).
   Tip: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py <domain>` reads a site in seconds
   and finds the company LinkedIn page; subagents can use it before browsing further.
   The subagents must open the company's **own** website; a local office of a large group
   counts as the group; an unreadable site is `unknown`, never `no`.
4. Validate + dry run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py apply-research --file <file> --store-all`
   Fix refused lines. Then `--commit`.
5. **Disqualifying is a one-way door.** Do not set any account to `disqualified` yourself.
   Show the user the full `fit = no` list with reasons; only after a clear yes, update the
   status with a query they approve.
6. Report: fits, not fits (top reasons), unknowns (why). Add a row in the Learnings table to
   `directives/icp.md` if a pattern appears (e.g. "half the list were agencies").
