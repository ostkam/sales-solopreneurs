# 🧭 How this workspace runs

> This folder is a small AI-native sales operation. The AI agent runs it together with
> the owner. **Agent: read this file first, every session.**

---

## The idea

A language model is great at judgment and bad at doing the same thing the same way a
hundred times. A script is the opposite. So the work is split in three, and each part
does only what it is good at:

```
   📘 Playbooks            🤖 The agent              ⚙️ Tools
   directives/*.md   ─►    reads, judges,     ─►    gtm.py, site_read.py
   what we do + why        runs the tools,          exact, repeatable,
   what we learned         improves playbooks        no AI inside
                                   │
                                   ▼
                          🗄️ data/gtm.db (local)
```

| Part | Lives in | Its job |
|---|---|---|
| 📘 **Playbooks** | `directives/` | What we do and why: ICP, personas, signals, message rules, and what we learned. Plain Markdown that a human reads and edits. |
| 🤖 **The agent** | this conversation | Read the playbook, decide, judge (is this company a fit? what is true about this person?), run the tools, improve the playbook. |
| ⚙️ **Tools** | `gtm.py`, plugin scripts, `execution/` | Everything that must be exact: the database, imports, validation, exports, reading websites. |

The database is one local file, `data/gtm.db` (SQLite). Nothing leaves this computer
unless the owner exports it.

---

## 🛡️ Rules that keep it safe

| # | Rule | In practice |
|---|---|---|
| 1 | **Judgment goes through a file** | Many judgments → one JSON line each in `.tmp/` → a `gtm.py` command checks the file and writes it. One bad line and the whole file is refused. |
| 2 | **Dry run first** | Every command that writes shows its plan first. Read it, then add `--commit`. |
| 3 | **Never overwrite a human** | Imports only fill empty fields. |
| 4 | **One-way doors need a yes** | Disqualifying a company, deleting data, sending anything: show the list, wait for a clear yes. |
| 5 | **Unreadable is not "no"** | A website that does not load means `unknown`, never a rejection. |
| 6 | **Do-not-contact wins** | `gtm.py suppress` adds to the list; every import and export checks it. |
| 7 | **Only true facts in messages** | Use what the profile or post shows. Never invent common ground, a mutual friend or a result. |

---

## ⚡ How to work

- **Use the skills.** Each step is a skill: `start`, `read-website`, `icp`, `persona`,
  `hiring-signal`, `signal-builder`, `linkedin`, `pipeline`. Before writing a new script,
  check whether a skill or a `gtm.py` command already does it.
- **Many items: use subagents.** Split research into batches of 5 to 10, one subagent per
  batch. Subagents do not start their own subagents, and each one appends its JSON lines to
  its own file as it goes, so a crash loses nothing.
- **Ask, do not guess.** When a playbook does not cover a case, ask the owner one short
  question, then write the answer into the playbook.

---

## 🔁 When something breaks or surprises you

1. Read the error. Fix the cause, not the symptom.
2. Test the fix on one item before you run it on many.
3. Write what you learned in the **Learnings** table of the playbook it belongs to, with
   the date. _Example: "job boards list recruiters as employers → added their names to the
   skip list"._

The playbooks get better every week this way. That is the point: the system learns from
its own runs.

---

## 📁 Folder map

| Path | What it is |
|---|---|
| `CLAUDE.md` / `AGENTS.md` | This file (AGENTS.md is the same text for other agent tools) |
| `directives/` | The playbooks: `icp.md`, `personas.md`, `signals.md` + `signals/` specs, `linkedin.md` |
| `execution/` | Your own extra scripts, if you add any |
| `data/gtm.db` | The database (private, never committed) |
| `input/` | Files you drop in: CSV exports, pasted lists |
| `.tmp/` | Working files: website reads, research lines, drafts (safe to delete) |
| `gtm.py` | Shortcut to the database tool: `python3 gtm.py status`, `pipeline`, `query "select …"` |
| `python3 gtm.py ui` | Live read-only view in the browser (localhost): Profile, Today, Accounts, Contacts, Signals. Run it in the background. |
