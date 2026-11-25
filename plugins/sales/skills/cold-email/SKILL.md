---
name: cold-email
description: Write signal-based cold emails in the Seen, So, Small yes shape (one specific observation, why it usually matters, a small free offer with a clean exit, a yes/no reply), validate them, and export a CSV for any email sequencer. Never sends anything itself.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write Edit
---

# Cold email

1. Read `directives/cold_email.md` (shape, rules, learnings).
2. Pick recipients with an email and a live signal:
   `gtm.py query "select c.id, c.first_name, c.email, a.name, a.domain, s.detail from contacts c join accounts a on a.id=c.account_id join signals s on s.account_id=a.id and s.active=1 where c.email is not null"`
   No email yet: run `enrich` first. Never email someone on the do-not-contact list.
3. For each person write one email:
   - **Seen**: their signal, specific and checkable (the role they hire, or a fact
     from their website in `.tmp/sites/<domain>/pages.json`). One only.
   - **So**: why it usually matters, conditional, no invented numbers.
   - **Small yes**: a small thing you will make for them + how long it takes them + a
     clean exit. Then "Reply yes and I'll make it." and the user's first name.
   - Subject: 2-4 plain words about them ("Your bookkeeping hire").
4. Draft lines in `.tmp/drafts/<date>_email.jsonl`:
   `{"contact_id": 7, "kind": "email", "subject": "...", "body": "...", "basis": "the signal or page it is based on"}`
5. `gtm.py check-drafts --file <file>` until valid; show 2-3 to the user for approval;
   then `apply-drafts --file <file> --commit`.
6. `gtm.py export-emails --out .tmp/emails_for_sequencer.csv` and tell the user to import
   it into their sequencer (Instantly, Lemlist, Smartlead, Apollo...). Warm up new
   sending domains first; never send cold email from your main domain.
7. When sent: `log-touch --channel email --kind email --commit` per person (or ask the
   user to export sent/replied from the sequencer and log replies).

Timing: email goes a few days after the LinkedIn invite, never the same day as a DM.
