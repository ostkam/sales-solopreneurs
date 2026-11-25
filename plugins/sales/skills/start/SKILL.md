---
name: start
description: The guided start. Leads the user step by step through the whole flow - workspace, reading their website, ICP, personas, their first buying signal, first LinkedIn note - running each step, explaining it in one or two lines, and waiting for a go between steps. Use when the user says start, let's start, get started, guide me, or does not know where to begin.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py *) Read Write Edit Agent WebSearch WebFetch
---

# Start: the guided flow

You are the guide. The user never needs a command name: you run each step, explain it in
one or two plain lines, show the result as a small table, and wait for a "go" before the
next step. The whole flow takes about 10 to 15 minutes.

If the user only asks to start or open the **CRM**, dashboard or live view, do not run this
flow: start `gtm.py ui` in the background (see the `pipeline` skill) and give the URL.

Keep a progress file `.tmp/guide.json` (`{"domain": "...", "done": ["workspace", ...]}`).
If it exists when the user starts, offer to resume where they stopped.

## Step 0: two questions (one message)
"Let's build your sales system. Two things to start:
1. Your website.
2. In one sentence: what do you sell, and to whom?"

## Step 1: workspace
If `CLAUDE.md` or `data/gtm.db` is missing, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py init`.
Say: "This folder is now a small sales system: playbooks I follow, a local database, and
tools that do the exact work." Show the folder tree (short).
Then start the live view **in the background**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py ui`
(it opens the browser). Say: "This page is your database. It fills up by itself while we
work; new rows flash." Give the URL it printed. If it does not open, continue without it.
Then: "Next: I read your website to learn your business. Go?"

## Step 2: read the website
Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py <domain>` (progress shows per page).
Then, as in the `read-website` skill, show a short table of what you learned, each row
with its page: what they sell, to whom, industries, proof (customers, results), regions
and languages, company LinkedIn. Say what was not found.
If the site blocks automated reading (exit code 2), say so in one line and continue from
the one-sentence description.
Then: "Next: I turn this into your ideal customer profile. Go?"

## Step 3: ICP
Follow the `icp` skill: fill the 11 parameters from `.tmp/sites/<domain>/pages.json` and the
one-sentence answer, with sources. Show what you already found ("found on your site: n of
11"). Ask **exactly 5 numbered questions** in one message, each with your guess, and end
with: "Answer like `1 ... 2 ...`; one line each; 'skip' is fine."
Write `directives/icp.md`, run `gtm.py profile-check icp`, show the result in two lines.
Then: "Next: who inside those companies we talk to. Go?"

## Step 4: personas
Follow the `persona` skill, short version: one or two personas, **3 numbered questions**.
The 3rd question is always about the user: "Two true facts about your own background, and
one line for who you are now (e.g. 'now a founder helping small agencies with AI')". These
go into the background table in `directives/linkedin.md`; every LinkedIn note uses them.
Write `directives/personas.md`. Show the titles list: "These are the titles we will search for."
Then: "Next: the signal that tells you a company needs you right now. Go?"

## Step 5: your first buying signal
Explain in one line: "A signal is a public, dated event that makes a company likely to need
you now; it also gives you the first line of your message."
1. From the ICP `triggers`, propose 2-3 candidate signals (one line of logic each) and
   recommend one. **Hiring** is usually the fastest to test live, because a job ad names
   the pain and LinkedIn Jobs gives results in seconds; use it unless another signal is
   clearly better for this business.
2. **Hiring:** fill the map in `directives/signals/hiring.md` with 1-2 rows ("when a company
   hires a ..., it usually means ..."), confirm with one yes/no, tell the user exactly what
   to search on LinkedIn Jobs (words, location, "Past week"), and ask them to paste the
   results page. Triage the paste (recruiters, big groups, wrong roles), research the
   **first 3** kept employers with one `account-researcher` subagent ("say 'all' for every
   one"), then `gtm.py apply-research` dry run, show, commit. Show the fit table.
   **Another signal:** follow the `signal-builder` skill to write its spec in
   `directives/signals/<name>.md`, and tell the user how to collect the first batch; run it
   now only if it takes under 3 minutes.
Then: "Next: the first message to a real person. Go?"

## Step 6: first LinkedIn note
Ask the user for the people at one fit company: either a **Sales Navigator people list**
(the company's people page, all text copied) or directly **one person's profile**.
- If they paste a **list**: import it (`import-contacts --file input/paste_<company>.txt
  --account-domain <domain>`, dry run), pick the 1-2 best people with one reason each,
  commit only those, then ask: "Please open <name>'s profile, select all text (About,
  Experience, Activity) and paste it here." **Do not write any opener before that
  profile is pasted.** Save the facts with `gtm.py profile-facts --contact-id <id> --facts "..." --commit`.
- If they paste **one profile**: save the person with
`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py add-contact --company "<company>" --domain <domain> --first <first> --last <last> --title "<title>" --facts "<2-4 profile facts you will use>" --commit`
  (it creates the account if needed and prints the contact id).

Then, as in the `linkedin` skill:
1. Show why the rules exist: write a typical pitchy note ("Hi X, I help companies like
   yours... free demo call?") to the drafts file and run `gtm.py check-drafts`; show the
   validator refusing it and why. One line of explanation.
2. Write the real note (3 to 6 words about them, true common ground, who you are now),
   validate it, and save it with `apply-drafts --commit`.
Say: "Nothing is sent. You copy it into LinkedIn yourself; tell me when it is sent, and I log it."

## Step 7: wrap-up
Run `gtm.py status` and `gtm.py pipeline`, and point to the **Today** tab of the live view.
Show in 5 lines what now exists: playbooks (ICP, personas, signal spec, LinkedIn), n accounts, n signals, 1 note
ready. Then list what the user can ask for next, in plain words: "build another signal",
"find more companies hiring ...", "import people from a Sales Navigator page", "write cold
emails for the fits", "what should I do today?", "learn from my results". Mark the flow
done in `.tmp/guide.json`.

## Rules for the guide
- One step at a time. Never run two steps without a "go" (Enter, "go", "yes", "next" all
  count). "skip" jumps a step; "stop" ends and keeps the progress.
- Short, concrete narration, no jargon. Results as small tables.
- If a step fails, say what happened in one line, offer the fallback, and continue. The
  flow must never get stuck.
