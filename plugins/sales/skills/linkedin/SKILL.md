---
name: linkedin
description: LinkedIn outreach in two steps - a personal connect note (no pitch) and, after they accept, a follow-up DM built on the signal. Writes each message from the person's profile and the user's real background, validates it (length, banned words, true basis), stores drafts, and logs invites, accepts and replies.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write Edit
---

# LinkedIn: connect, then follow up

Read `directives/linkedin.md` first, every time. It holds the shapes, the rules and the
user's background. If "My background for common ground" is empty, ask the user for 2-3
true career facts and their one-line "who I am now", and write them there.

## 1. Connect note
For each chosen person (`gtm.py query "select c.id, c.first_name, c.last_name, c.title, c.profile_facts, a.name from contacts c join accounts a on a.id=c.account_id where ..."`):
1. **Always ask for the full profile first, one person at a time.** A line from a Sales
   Navigator or search list (name, title, tenure) is never enough for a note. Ask:
   "Please open <name>'s LinkedIn profile, select all text (About, Experience, Activity)
   and paste it here." Wait for it. Save what you will use:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py profile-facts --contact-id <id> --facts "<3-6 facts: current work, a recent post, background>" --commit`
   Use only what the profile shows. If the profile has almost nothing, say so and write
   from their current role, never from a guess.
2. Pick what to appreciate (order in the playbook: recent post, their work, a value, an
   unusual path). Say it in **3 to 6 of your own words**. Never cite their headline.
3. Pick the **one** background fact that truly overlaps with them.
4. Offer 1-2 versions with the reason for each; recommend one. The user decides.
5. Write the chosen note to `.tmp/drafts/<date>_linkedin.jsonl`:
   `{"contact_id": 12, "kind": "linkedin-connect", "body": "Hi Ana, ...", "basis": "profile fact the note is based on"}`
6. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py check-drafts --file <file>`; fix until valid,
   then `apply-drafts --file <file> --commit`.
7. When the user says it was sent:
   `gtm.py log-touch --contact-id 12 --channel linkedin --kind invite --body "<note>" --commit`

Pacing advice: 1-2 people per company at a time (different teams), stay well under
LinkedIn's weekly invite limit, and withdraw invites that are open after about 3 weeks.

## 2. Follow-up DM (after they accept)
1. Log it: `log-touch --contact-id N --channel linkedin --kind accepted --commit`.
2. Write the DM in the playbook shape: thanks, **what you saw** (the account's signal:
   `gtm.py query "select type, detail, source_url from signals where account_id=..."`),
   why it usually matters, a small useful offer with a clean exit, a yes/no question.
3. Same draft flow with `"kind": "linkedin-dm"`. After sending: `--kind message`.
4. Replies: `--kind reply --body "<their words>" --outcome positive|neutral|negative`.

## 3. What to do today
`gtm.py pipeline` lists who accepted without a DM, which invites are stale, and fresh replies.
