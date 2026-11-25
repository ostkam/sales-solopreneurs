---
name: persona
description: Define 1-3 buyer personas inside ICP companies - 8 fixed parameters each (titles, department and seniority, decision role, pains, desired result, objections, trusted proof, channel and language). Drafts from the ICP and website, then asks 5 numbered questions. Writes directives/personas.md.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Edit
---

# Persona: who inside the company

1. Read `directives/icp.md` (run `icp` first if it is mostly missing) and the website's
   `.tmp/sites/<domain>/pages.json` if present (testimonials and case studies often name the buyer's role).
2. Draft 1 to 3 personas, usually: the one who **signs**, the one who **feels the pain
   first**, and sometimes the one who **uses** the result. For a small-company ICP, one
   persona (the founder or owner) is often enough.
3. Fill the 8 parameters for each with value, source and confidence (`✅ found`,
   `🟡 inferred`, `⬜ missing`), like the ICP. Keep each cell short and on one line.
   **titles** must be a comma-separated list of lowercase title words: `import-leads`
   uses it to tag people (e.g. `founder, ceo, owner, managing director`).
4. Ask **exactly 5 numbered questions** in one message (plain list, no menus), missing
   items first, each with your guess. Typical: who signs, what they complain about in
   their own words, the objection you hear most, what proof convinces them, their language.
   Wait for `1 ... 2 ...` answers.
5. Write `directives/personas.md`: one `## Persona: <name>` section per persona, copying
   the three small tables of the template (keep the `## Persona:` heading format exactly;
   tools read it).
6. Also fill the **"My background for common ground"** table in `directives/linkedin.md`
   if empty: ask the user for 2-3 true facts about their own career, and the one-line
   "who I am now". The LinkedIn notes are built from these.
7. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py profile-check persona`. Next: a signal
   skill (`hiring-signal`) or `import-leads`.
