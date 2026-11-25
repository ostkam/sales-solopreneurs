---
name: hiring-signal
description: The worked example of a buying signal - turn job ads into qualified accounts. Define the map (they hire role X, so they have pain Y, which my offer Z solves), then paste a job board results page or careers URLs; the skill filters recruiters and wrong sizes, researches each employer with subagents, and stores fits with the ad as a dated signal.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write Edit Agent
---

# Hiring signal

This is the built-in example of a signal; the spec lives in `directives/signals/hiring.md`.
To build a different signal, use the `signal-builder` skill.

## A. Define the map (once)
If the map in `directives/signals/hiring.md` has no real rows, build it with the user:
ask which 1-3 roles, when a company hires them, mean a pain the user's offer solves
(use the ICP `triggers` as a starting point). Write rows: role, pain, offer, search words.
Then tell the user how to search: on LinkedIn Jobs (or any job board), search the words,
filter "Past 24 hours" or "Past week", and copy the results pages (pages 1-3 are usually
enough; later pages drift away from the search).

**Never scrape LinkedIn or job boards with a script.** The user pastes; you read.

## B. Triage the paste (you, no subagents)
1. Save the paste to `.tmp/signals/<date>_paste.txt`.
2. Extract each ad: employer, title, location, age. Group ads by employer.
3. Drop, and count why: recruiters (names in `signals/hiring.md` + obvious agencies), employers
   already in the DB (`gtm.py query "select name, domain from accounts"`), well-known
   large groups outside the ICP size, roles that do not match the map (same title,
   different job), duplicates.
4. Show a short table: kept employers vs dropped (with reasons).

## C. Research (subagents)
- Split the kept employers into batches of 5 to 8 and give each batch to one
  `account-researcher` subagent (in parallel). Give each: the batch lines, the fit rule
  from `directives/icp.md`, the hiring map row, and its output path
  `.tmp/research/<date>_hiring_<batch>.jsonl`.
- Each writes one line per employer:
  `{"company": "...", "domain": "x.com", "fit": "yes|no|unknown", "reason": "...", "country": "...", "size_employees": 120, "industry": "...", "signal": {"type": "hiring", "detail": "<ad title>", "source_url": "<ad URL if found, else null>", "observed_at": "YYYY-MM-DD"}}`

## D. Store (validator, dry run, commit)
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py apply-research --file .tmp/research/<file>.jsonl --source "hiring signal <date>"
```
Read the dry run. If the file is REFUSED, fix the named lines and run again. Then add
`--commit`. Show the user the fits: company, size, the role, why it fits.

## E. Learn
Add one row to the **Learnings** table in `directives/signals/hiring.md`: date, ads pasted, employers
kept, fits, and any new recruiter names (add those to the skip list too).
Next for the fits: `import-leads` (find 1-2 people per account).
