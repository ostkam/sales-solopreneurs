---
name: signal-builder
description: Define your own buying signals with AI. Describe what usually happens at a company just before it buys from you; the skill turns it into a signal spec (meaning, source, detection rules, verification, freshness, first line), adds it to the catalog, and runs a small test batch to measure the yield. Use to create, test, tune or stop a signal.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/gtm.py *) Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/site_read.py *) Read Write Edit Agent WebSearch WebFetch
---

# Signal builder

A signal is a public, dated event that makes a company more likely to need you now. Every
business has different ones. This skill helps the user find and build theirs.

## 1. Find candidate signals (a short conversation)
Read `directives/icp.md` (especially `triggers`) and `directives/personas.md`. Then ask
**3 numbered questions** in one message:
1. "Think of your last 3 customers. What was happening at their company just before they
   contacted you or said yes?"
2. "What would a company have to post, announce or search for, so you would know they
   need you this month?"
3. "Where would you see that: job ads, their website, news, LinkedIn, events, something else?"

From the answers plus the ideas table in `directives/signals.md`, propose **2-3 candidate
signals**. For each: one line of logic ("they do X, which means Y, so my offer Z"), the
source, and a rough guess of volume and noise. Recommend one to build first: observable,
dated, and checkable from public sources.

## 2. Write the spec
Copy `directives/signals/_template.md` to `directives/signals/<name>.md` and fill every
section with the user: meaning, where to see it, include/exclude rules, the questions the
research subagent must answer, what to store, freshness, and the first line it gives.
`directives/signals/hiring.md` is a complete worked example to follow.
Add a row to the catalog in `directives/signals.md` with status `testing`.

Rules for a good signal:
- **public and dated**: someone could check it and say when it happened;
- **specific**: "hiring a bookkeeper", not "growing";
- **collectable without scraping**: a paste, a CSV, a list of URLs, or company sites read
  with `site_read.py`. Never scrape LinkedIn or sites that forbid it;
- **one pain**: if it can mean many things, add a verification question that settles it.

## 3. Test it on a small batch
1. Tell the user exactly how to collect a first batch (what to search, which filter, what
   to paste or export), or, for website-based signals, list 10-20 account domains and run
   `site_read.py` on each.
2. Apply the **detection rules** yourself first (no AI needed): keep / drop with reasons.
3. Give the kept items to `account-researcher` subagents (batches of 5-8) with the spec's
   verification questions and the ICP fit rule. Each line carries
   `"signal": {"type": "<name>", "detail": "...", "source_url": "...", "observed_at": "YYYY-MM-DD"}`.
4. `gtm.py apply-research --file .tmp/research/<file>.jsonl` (dry run, then `--commit`).

## 4. Measure and decide
Write one row in the Learnings table in the spec: "<date>: <n> collected → <n> kept → <n> fits;
noise: <main reason>". Then with the user: keep testing, tune the rules (a new exclude
word, a stricter title), mark it `active`, or `stopped` with the reason. A signal that
gives 1 fit per 50 items can still be worth it if collecting takes 5 minutes; a signal
that needs an hour for 0 fits is not.

## Later runs
"Run the <name> signal" = steps 3-4 with the current spec. Re-check old signals after the
freshness period and close the ones that are gone (`gtm.py close-signal --id N --commit`).
