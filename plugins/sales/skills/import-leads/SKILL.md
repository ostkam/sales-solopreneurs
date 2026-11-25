---
name: import-leads
description: Import people and companies from a LinkedIn or Sales Navigator page pasted as text, or from any CSV (Sales Navigator export, PhantomBuster, Apollo, a spreadsheet). Matches people to accounts, tags each with a persona from its title, never overwrites, respects the do-not-contact list.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write
---

# Import leads

## Accounts (companies)
CSV with any of: company/name, website/domain, linkedin, employees, country, industry.
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py import-accounts --file input/<file>.csv --source "<where from>"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py import-accounts --domains a.com b.com --source "manual"
```

## People
1. **Pasted page** (fastest): the user opens a company's people list in Sales Navigator,
   selects all text, copies, pastes into the chat. Save it as `input/paste_<company>.txt`.
   The first line must be the company name; if it is not, pass `--account-domain`.
2. **CSV**: any export with first/last name (or full name), title, company, LinkedIn URL;
   optional email, phone.
3. **From the company website**: `read-website` lists people named on team/about pages;
   save the ones that match a persona with `add-contact`.
4. **One person** (a single pasted profile):
   `gtm.py add-contact --company "<c>" --domain <d> --first <f> --last <l> --title "<t>" --facts "<profile facts>" --commit`

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py import-contacts --file input/paste_<company>.txt --account-domain <domain>
```
Read the dry run: each person, title, persona tag, connection degree, account.
- `NO ACCOUNT`: import the company first, or pass `--account-domain`.
- `no persona`: the title matches no `titles` keyword in `directives/personas.md`.
  Either skip the person or add the word to the persona.

## Choose who to contact (judgment, before commit)
From the paste, pick **1-2 people per company**, not everyone:
- the persona that **signs** first, plus at most one other in a **different team or country**;
- prefer 2nd degree (and people with mutual connections: an introduction beats any note);
- skip people far from the decision (other regions, after-sales, juniors) unless the
  persona says otherwise.
Show your pick with one reason each, then commit only those (`--skip "Full Name" ...` for
the rest) with `--commit`.

Paste privacy: if a paste contains private content (a chat window, messages), ignore that
part and do not save it.
## Before any opener: the full profile
A pasted list gives names and titles, not enough to write a personal note. For each chosen
person, **one at a time**, ask the user to paste the person's full profile page text
(About, Experience, Activity), save the facts with `gtm.py profile-facts`, and only then
write the note (`linkedin` skill). Never write openers for the whole list at once.

Next: `linkedin` for the chosen people (profile first), or `enrich` for emails and phones.
