---
name: init
description: Build an AI-native sales workspace in the current folder - the 3-part system (playbooks in directives/, the AI as operator, deterministic tools) plus a local SQLite database. Use first, in an empty or existing project folder. Safe to run again.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *)
---

# Init: build the workspace

1. Confirm the folder with the user in one line: "I'll set up the workspace in `<cwd>`. OK?"
   If the folder already has unrelated files, suggest a new folder instead.
2. Run:
   ```
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py init
   ```
   It creates `CLAUDE.md` + `AGENTS.md` (how the workspace runs), `directives/` (the
   playbooks), `execution/`, `input/`, `.tmp/`, `data/gtm.db` (SQLite), `.gitignore`,
   `.env.example`, and a `gtm.py` shortcut. It never overwrites existing files.
3. Read the new `CLAUDE.md` yourself: from now on you follow it in this folder.
4. Show the user the folder tree and explain the three parts in 3 short lines:
   - **Playbooks** (`directives/`): what we do and what we learned. Human-readable.
   - **You, the AI**: read the playbooks, judge, run the tools, improve the playbooks.
   - **Tools** (`gtm.py`): the database and every exact step. No AI inside.
5. Next step to suggest: "Give me your website; I'll read it, then we define your ICP." (or just say `start`)
