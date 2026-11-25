---
name: enrich
description: Add work emails and phone numbers to contacts from any data provider (Apollo, Prospeo, Hunter, Kaspr, Lusha...) by importing the provider's CSV export. Fills empty fields only, records the source, and skips anything on the do-not-contact list.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read
---

# Enrich: emails and phones

1. Export the people to enrich:
   `gtm.py query "select c.first_name, c.last_name, a.name as company, a.domain, c.linkedin_url from contacts c join accounts a on a.id=c.account_id where c.email is null"`
   Save as CSV in `input/` and upload it to the provider of the user's choice. LinkedIn
   URL + name + company domain give the best match rate.
2. Download the provider's result CSV into `input/`, then:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py import-enrichment --file input/<result>.csv --provider "<name>"
   ```
   It matches by LinkedIn URL, then by name + company, and fills only empty email/phone
   fields (with status and source). Read the dry run, then `--commit`.
3. Report how many got an email, how many a phone, and how many verified emails.

## Rules to tell the user
- Use only **verified** (or "valid") emails for cold email; "catch-all" and "unknown"
  bounce more and hurt the sending domain.
- Phone numbers: check the local rules before any call (do-not-call registries, consent
  rules for mobile numbers). Store the source; delete numbers you will not use.
- Someone asks not to be contacted: `gtm.py suppress --kind email --value <x> --reason "asked" --commit`
  (also `phone`, `linkedin`, `domain`). It applies to every future import and export.

Provider API calls are not built in: an export/import keeps keys out of the workspace and
works with any provider. If the user wants an API integration, write it as a script in
`execution/` that outputs the same CSV format, dry run first.
