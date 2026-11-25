---
name: warm-network
description: Put warm paths first - 1st and 2nd degree connections, mutual connections, former colleagues and old customers - by importing a LinkedIn connections export or a pasted list and marking which accounts and people have a warm way in.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Read Write
---

# Warm network

People answer people they know. Before cold outreach, check who is already close.

1. **Your 1st-degree connections**: LinkedIn, Settings, Data privacy, Get a copy of your
   data, Connections. The CSV has first name, last name, URL, company, position.
   Import companies that match the ICP with `import-accounts`, people with
   `import-contacts --source "my connections"`; they are 1st degree.
2. **Mutual connections**: when a pasted profile shows "You both know X", note it in the
   contact's facts. An introduction request beats any cold note: draft a short ask to X.
3. **Old customers and colleagues** (the user's own records only): ask which ones the user
   knows personally. Use only contact data the user has the right to use (their own
   relationship, not a former employer's database).
4. Messages to warm contacts are different: no connect-note rules; write like a person
   catching up (what you did together, what you do now, one honest question).
5. `gtm.py query "select c.first_name, c.last_name, a.name from contacts c join accounts a on a.id=c.account_id where c.connection_degree in ('1st','2nd')"`
   gives the warm list; work it before the cold one.
