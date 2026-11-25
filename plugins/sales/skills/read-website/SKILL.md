---
name: read-website
description: Read a company website and pull out plain facts - what they sell, to whom, industries, locations, languages, team, company LinkedIn page, contact details - with the page each fact came from. Use for your own site during onboarding, and to enrich accounts and find people at prospects.
argument-hint: <domain>
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write
---

# Read a website

## Run
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py <domain>
```
It reads the homepage and up to 9 informative pages (about, offer, customers, industries,
team, contact, pricing, careers), 4 at a time, in about 2 to 20 seconds, and writes
`.tmp/sites/<domain>/pages.json` (page texts) and `facts.json` (title, headline, languages,
company LinkedIn, emails, phones, schema.org data). Exit code 2: the site blocks automated
reading; say so and work from what the user tells you.

The script judges nothing. **You** read the files and write the summary.

## Summarise (always cite the page)
A short table, each row with the page URL it came from:
- what they sell (one sentence a buyer would understand)
- who they sell to (customer type, industries, size if visible)
- proof (named customers, case studies, numbers)
- regions and languages
- company LinkedIn page; how to contact them
- people named on team/about pages (name, role)

Say what was **not** found (e.g. "no prices", "no team page"), never guess it.

## What to do with it
- **Your own site (onboarding):** go on with the `icp` skill; it uses `pages.json` to draft
  the ICP, so only the gaps become questions.
- **A prospect (account enrichment):** store a 1-2 sentence description and the company
  LinkedIn URL in a research line and apply it:
  `{"company": "...", "domain": "...", "fit": "yes|no|unknown", "reason": "...", "description": "...", "linkedin_url": "..."}`
  → `gtm.py apply-research --file .tmp/research/<file>.jsonl --store-all` (dry run, then `--commit`).
- **Finding people:** for people named on the team page who match a persona, save them with
  `gtm.py add-contact --company ... --domain ... --first ... --last ... --title ... --facts "named on <page>" --commit`.
  Use only work contact details the company itself publishes.
