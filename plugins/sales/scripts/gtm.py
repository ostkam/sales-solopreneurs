#!/usr/bin/env python3
"""gtm.py: the deterministic layer of an AI-native sales workspace.

Claude decides; this script does. It owns the local SQLite database (data/gtm.db),
imports, validation and exports. No LLM calls, no network (`ui` serves on 127.0.0.1 only).
Every command that writes is a DRY RUN unless you add --commit.

Run from the workspace folder (the one `init` created):

    python3 gtm.py init                          # build the workspace (safe to re-run)
    python3 gtm.py status                        # what is in the database
    python3 gtm.py profile-check icp|persona     # are the parameters filled?
    python3 gtm.py import-contacts --file paste.txt|people.csv [--account-domain d] [--commit]
    python3 gtm.py add-contact --company C --domain d --first F --last L --title T [--facts ..] [--commit]
    python3 gtm.py profile-facts --contact-id N --facts "from the full profile" [--commit]
    python3 gtm.py apply-research --file .tmp/research/x.jsonl [--commit]
    python3 gtm.py signals [--active] / close-signal --id N --commit
    python3 gtm.py check-drafts --file .tmp/drafts/x.jsonl     # validate connect notes and DMs
    python3 gtm.py apply-drafts --file .tmp/drafts/x.jsonl [--commit]
    python3 gtm.py log-touch --contact-id N --channel linkedin --kind invite [--body ..] --commit
    python3 gtm.py suppress --kind email|phone|domain|linkedin --value V --reason R --commit
    python3 gtm.py pipeline [--html .tmp/pipeline.html]
    python3 gtm.py query "SELECT ..."            # read-only SQL
    python3 gtm.py set-company --domain d [--name N] [--commit]   # your own company (Profile tab)
    python3 gtm.py ui [--port 8765] [--no-open]  # live read-only view in the browser
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = PLUGIN_ROOT / "templates"
WS = Path.cwd()
DB_PATH = WS / "data" / "gtm.db"

# ----------------------------------------------------------------------------- schema
MIGRATIONS = [
    # 1: base schema
    """
    CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS segments (
        name TEXT PRIMARY KEY, hypothesis TEXT, status TEXT DEFAULT 'testing', started_at TEXT);
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL, domain TEXT UNIQUE, linkedin_url TEXT,
        country TEXT, size_employees INTEGER, industry TEXT, segment TEXT,
        fit TEXT DEFAULT 'unknown' CHECK (fit IN ('yes','no','unknown')), fit_reason TEXT,
        status TEXT DEFAULT 'new' CHECK (status IN ('new','active','customer','disqualified')),
        source TEXT, notes TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY, account_id INTEGER REFERENCES accounts(id),
        first_name TEXT, last_name TEXT, title TEXT, persona TEXT, location TEXT,
        linkedin_url TEXT UNIQUE, connection_degree TEXT, profile_facts TEXT,
        email TEXT, email_status TEXT, email_source TEXT,
        phone TEXT, phone_type TEXT, phone_source TEXT,
        source TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY, account_id INTEGER REFERENCES accounts(id),
        contact_id INTEGER REFERENCES contacts(id), type TEXT NOT NULL, detail TEXT,
        source_url TEXT, observed_at TEXT, active INTEGER DEFAULT 1, checked_at TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS drafts (
        id INTEGER PRIMARY KEY, contact_id INTEGER REFERENCES contacts(id),
        channel TEXT, kind TEXT, subject TEXT, body TEXT, basis TEXT,
        status TEXT DEFAULT 'draft' CHECK (status IN ('draft','sent','dropped')), created_at TEXT);
    CREATE TABLE IF NOT EXISTS touches (
        id INTEGER PRIMARY KEY, contact_id INTEGER REFERENCES contacts(id),
        channel TEXT, kind TEXT, body TEXT, outcome TEXT, at TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS verdicts (
        id INTEGER PRIMARY KEY, kind TEXT, subject TEXT, result TEXT, reason TEXT,
        source_file TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS suppression (
        id INTEGER PRIMARY KEY, kind TEXT, value TEXT, reason TEXT, created_at TEXT,
        UNIQUE(kind, value));
    CREATE INDEX IF NOT EXISTS ix_contacts_account ON contacts(account_id);
    CREATE INDEX IF NOT EXISTS ix_signals_account ON signals(account_id);
    CREATE INDEX IF NOT EXISTS ix_touches_contact ON touches(contact_id);
    """,
    # 2: what the company does, in a sentence or two (from its website)
    """
    ALTER TABLE accounts ADD COLUMN description TEXT;
    """,
]

TOUCH_KINDS = {"invite", "accepted", "message", "reply", "email", "bounce", "meeting", "withdrawn", "note"}
CHANNELS = {"linkedin", "email", "phone", "event", "other"}


def now() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat()


def connect(must_exist: bool = True) -> sqlite3.Connection:
    if must_exist and not DB_PATH.exists():
        sys.exit("No database here. Run `init` in your workspace folder first.")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def migrate(con: sqlite3.Connection) -> int:
    con.executescript(MIGRATIONS[0])  # every statement is IF NOT EXISTS: safe on any version
    row = con.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    version = int(row["value"]) if row else 1
    for i, sql in enumerate(MIGRATIONS[1:], start=2):
        if version < i:
            con.executescript(sql)
            version = i
    version = max(version, 1)
    con.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)", (str(version),))
    con.commit()
    return version


def norm_domain(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = v.split("/")[0].split("?")[0]
    v = re.sub(r"^www\.", "", v)
    return v or None


def norm_li(v: str | None) -> str | None:
    if not v:
        return None
    v = v.strip().split("?")[0].rstrip("/").lower()
    return v.replace("http://", "https://") or None


def suppressed(con, kind: str, value: str | None) -> bool:
    if not value:
        return False
    return con.execute("SELECT 1 FROM suppression WHERE kind=? AND lower(value)=lower(?)",
                       (kind, value)).fetchone() is not None


def done(commit: bool, n: int, what: str) -> None:
    if commit:
        print(f"\ncommitted: {n} {what}")
    else:
        print(f"\nDRY RUN: {n} {what} would be written. Add --commit to write.")


# ----------------------------------------------------------------------------- init
GITIGNORE = """# private data: never commit
data/
.tmp/
.env
*.csv
"""
ENV_EXAMPLE = """# Optional: API keys for scripts you add yourself in execution/.
# This file is git-ignored; never paste keys into chat.
"""


def cmd_init(a) -> None:
    created = []
    for d in ["directives", "execution", "data", ".tmp/sites", ".tmp/research", ".tmp/drafts",
              ".tmp/signals", "input"]:
        p = WS / d
        if not p.exists():
            p.mkdir(parents=True)
            created.append(d + "/")
    # CLAUDE.md for Claude Code, AGENTS.md (same text) for other agent tools
    for src, dst in [(TEMPLATES / "CLAUDE.md", WS / "CLAUDE.md"), (TEMPLATES / "CLAUDE.md", WS / "AGENTS.md")]:
        if not dst.exists():
            shutil.copy(src, dst)
            created.append(dst.name)
    for src in sorted((TEMPLATES / "directives").rglob("*.md")):
        rel = src.relative_to(TEMPLATES / "directives")
        dst = WS / "directives" / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, dst)
            created.append(f"directives/{rel}")
    for name, body in {".gitignore": GITIGNORE, ".env.example": ENV_EXAMPLE}.items():
        if not (WS / name).exists():
            (WS / name).write_text(body)
            created.append(name)
    shim = WS / "gtm.py"
    if not shim.exists():
        target = str(PLUGIN_ROOT / "scripts" / "gtm.py")
        shim.write_text(
            "#!/usr/bin/env python3\n# Shortcut to the plugin's gtm.py so you can run `python3 gtm.py ...` here.\n"
            f"import runpy, sys\nsys.argv[0] = {target!r}\nrunpy.run_path({target!r}, run_name='__main__')\n")
        created.append("gtm.py (shortcut)")
    con = connect(must_exist=False)
    v = migrate(con)
    print(f"workspace: {WS}")
    print("created: " + (", ".join(created) if created else "nothing new (already set up)"))
    print(f"database: {DB_PATH.relative_to(WS)} (schema v{v})")
    print("\nNext: read your own website, then define your ICP and personas.")


def cmd_status(a) -> None:
    con = connect()
    for t in ["accounts", "contacts", "signals", "drafts", "touches", "verdicts", "suppression"]:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  {t:<12} {n}")
    fit = dict(con.execute("SELECT fit, count(*) FROM accounts GROUP BY fit").fetchall())
    act = con.execute("SELECT count(*) FROM signals WHERE active=1").fetchone()[0]
    print(f"\n  accounts by fit: {fit or '-'} | active signals: {act}")


# ----------------------------------------------------------------------------- profile (ICP / personas)
REQUIRED = {
    "icp": ["offer", "outcome", "industries", "company size", "regions", "customer type",
            "deal size", "triggers", "disqualifiers", "proof", "alternatives"],
    "persona": ["titles", "department and seniority", "decision role", "pains", "desired result",
                "objections", "trusted proof", "channel and language"],
}
EMPTY = {"", "-", "?", "tbd", "todo", "unknown", "n/a"}


def _plain(cell: str) -> str:
    """'**offer**' / '`offer`' / '_offer_' -> 'offer' (playbooks are formatted for humans)."""
    return re.sub(r"[*`_]", "", cell).strip()


def param_rows(path: Path) -> list[tuple[str | None, dict]]:
    """(persona section or None, row) for every row of a table whose header has both
    'Parameter' and 'Value' columns. Help tables (Parameter | Question | Example) are ignored."""
    out, header, section = [], None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+Persona:\s*(.+)$", line.strip())
        if m:
            section = m.group(1).strip()
        elif re.match(r"^##\s", line.strip()):
            section = None
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = [_plain(c) for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(line.replace("|", "").strip()) <= set("-: "):
            continue
        if header and header[0] == "parameter" and "value" in header:
            out.append((section, dict(zip(header, cells))))
    return out


def read_param_table(path: Path) -> list[dict]:
    return [r for _, r in param_rows(path)]


def cmd_profile_check(a) -> None:
    path = WS / "directives" / ("icp.md" if a.kind == "icp" else "personas.md")
    if not path.exists():
        sys.exit(f"{path} is missing. Run init.")
    rows = read_param_table(path)
    have = {}
    for r in rows:
        have.setdefault(r.get("parameter", "").lower(), []).append(r.get("value", ""))
    problems = 0
    for key in REQUIRED[a.kind]:
        vals = have.get(key, [])
        if not vals or all(v.strip().lower() in EMPTY for v in vals):
            print(f"  MISSING  {key}")
            problems += 1
        elif any(v.strip().lower() in EMPTY for v in vals):
            print(f"  PARTIAL  {key} (empty in at least one persona)")
            problems += 1
        else:
            print(f"  ok       {key}")
    print(f"\n{a.kind}: {'complete' if not problems else str(problems) + ' parameter(s) to clarify'}")
    sys.exit(1 if problems else 0)


def persona_titles() -> list[tuple[str, list[str]]]:
    """[(persona name, [title keywords])] from the 'titles' rows in directives/personas.md."""
    path = WS / "directives" / "personas.md"
    if not path.exists():
        return []
    out = []
    for section, r in param_rows(path):
        if section and r.get("parameter", "").lower() == "titles":
            kws = [k.strip().lower() for k in re.split(r"[,;/]", r.get("value", ""))
                   if k.strip() and k.strip().lower() not in EMPTY]
            if kws:
                out.append((section, kws))
    return out


def match_persona(title: str | None, table) -> str | None:
    t = (title or "").lower()
    for name, kws in table:
        if any(k in t for k in kws):
            return name
    return None


# ----------------------------------------------------------------------------- imports
def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f, dialect=dialect)]


def pick(row: dict, *names: str) -> str:
    for n in names:
        for k, v in row.items():
            if k == n or k.replace("_", " ") == n:
                if v:
                    return v
    return ""


def find_account(con, domain=None, linkedin=None, name=None):
    if domain:
        r = con.execute("SELECT * FROM accounts WHERE domain=?", (domain,)).fetchone()
        if r:
            return r
    if linkedin:
        r = con.execute("SELECT * FROM accounts WHERE lower(linkedin_url)=?", (linkedin,)).fetchone()
        if r:
            return r
    if name:
        rows = con.execute("SELECT * FROM accounts WHERE lower(name)=lower(?)", (name.strip(),)).fetchall()
        if len(rows) == 1:
            return rows[0]
    return None


def upsert_account(con, rec: dict, commit: bool) -> tuple[str, int | None]:
    """Insert, or fill empty fields of an existing account. Never overwrites a value."""
    hit = find_account(con, rec.get("domain"), rec.get("linkedin_url"), rec.get("name"))
    if hit:
        fills = {k: v for k, v in rec.items() if v not in (None, "") and hit[k] in (None, "")}
        if fills and commit:
            sets = ", ".join(f"{k}=?" for k in fills)
            con.execute(f"UPDATE accounts SET {sets}, updated_at=? WHERE id=?", (*fills.values(), now(), hit["id"]))
        return ("fill " + ",".join(fills)) if fills else "exists", hit["id"]
    if not commit:
        return "new", None
    rec = {k: v for k, v in rec.items() if v not in (None, "")}
    rec.update(created_at=now(), updated_at=now())
    cur = con.execute(f"INSERT INTO accounts ({','.join(rec)}) VALUES ({','.join('?' * len(rec))})", tuple(rec.values()))
    return "new", cur.lastrowid


PASTE_DEGREE = re.compile(r"^(1st|2nd|3rd)\b|(\d)(?:st|nd|rd|th) degree connection", re.I)


def parse_salesnav_paste(text: str) -> tuple[str | None, list[dict]]:
    """People from a Sales Navigator / LinkedIn search page copied as text.

    A person block starts at the line "Go to <Name>'s profile"."""
    lines = [l.rstrip() for l in text.splitlines()]
    account = next((l.strip() for l in lines if l.strip()), None)
    people = []
    starts = [k for k, l in enumerate(lines) if re.match(r"^Go to .+?[’']s? profile$", l.strip())]
    for idx, s in enumerate(starts):
        block = [l.strip() for l in lines[s + 1: starts[idx + 1] if idx + 1 < len(starts) else len(lines)] if l.strip()]
        if not block:
            continue
        p = {"name": block[0], "degree": None, "title": None, "company": None, "location": None, "facts": []}
        rest = block[1:]
        for j, l in enumerate(rest):
            m = PASTE_DEGREE.search(l)
            if m and not p["degree"]:
                p["degree"] = (m.group(1) or {"1": "1st", "2": "2nd", "3": "3rd"}.get(m.group(2), m.group(2) + "th")).lower()
                continue
            if l.startswith("·"):
                continue
            if p["degree"] and not p["title"]:
                parts = re.split(r"\s{2,}", l)
                p["title"] = parts[0]
                p["company"] = parts[1] if len(parts) > 1 else None
                if j + 1 < len(rest):
                    p["location"] = rest[j + 1]
                continue
            if re.search(r"in role|in company|mutual connection|recent post|About:|Recently hired|Shared groups", l):
                p["facts"].append(l)
            elif p["facts"] and p["facts"][-1] == "About:":
                p["facts"].append(l)
        if p["title"]:
            people.append(p)
    return account, people


def cmd_import_contacts(a) -> None:
    con = connect()
    path = Path(a.file)
    personas = persona_titles()
    people = []
    if path.suffix.lower() == ".csv":
        for r in read_csv(path):
            full = pick(r, "full name", "fullname", "name")
            first = pick(r, "first name", "firstname", "first")
            last = pick(r, "last name", "lastname", "last")
            if full and not first:
                first, _, last = full.partition(" ")
            people.append({"first": first, "last": last, "title": pick(r, "title", "job title", "position", "headline"),
                           "company": pick(r, "company", "company name", "companyname", "organization"),
                           "domain": norm_domain(pick(r, "domain", "company domain", "website", "company website")),
                           "linkedin": norm_li(pick(r, "linkedin", "linkedin url", "profile url", "linkedinprofileurl", "profileurl")),
                           "location": pick(r, "location"), "degree": pick(r, "connection degree", "degree"),
                           "email": pick(r, "email", "work email"), "phone": pick(r, "phone", "mobile", "phone number"),
                           "facts": pick(r, "summary", "about", "title description")})
    else:
        account_hint, parsed = parse_salesnav_paste(path.read_text(encoding="utf-8"))
        for p in parsed:
            first, _, last = p["name"].partition(" ")
            people.append({"first": first, "last": last, "title": p["title"], "company": p["company"] or account_hint,
                           "domain": None, "linkedin": None, "location": p["location"], "degree": p["degree"],
                           "email": "", "phone": "", "facts": " | ".join(p["facts"])})
    forced = find_account(con, norm_domain(a.account_domain)) if a.account_domain else None
    if a.account_domain and not forced:
        sys.exit(f"No account with domain {a.account_domain}. Import the account first.")
    skip = {s.lower() for s in a.skip}
    n, skipped = 0, 0
    for p in people:
        if f"{p['first']} {p['last']}".strip().lower() in skip:
            continue
        acc = forced or find_account(con, p.get("domain"), None, p.get("company"))
        if suppressed(con, "linkedin", p.get("linkedin")) or suppressed(con, "email", p.get("email")):
            print(f"  SKIP suppressed  {p['first']} {p['last']}")
            continue
        if not acc:
            print(f"  NO ACCOUNT       {p['first']} {p['last']:<20} company '{p.get('company')}' (use --account-domain)")
            skipped += 1
            continue
        persona = match_persona(p["title"], personas)
        hit = None
        if p.get("linkedin"):
            hit = con.execute("SELECT * FROM contacts WHERE linkedin_url=?", (p["linkedin"],)).fetchone()
        if not hit:
            hit = con.execute("SELECT * FROM contacts WHERE account_id=? AND lower(first_name)=lower(?) AND lower(last_name)=lower(?)",
                              (acc["id"], p["first"], p["last"])).fetchone()
        rec = {"account_id": acc["id"], "first_name": p["first"], "last_name": p["last"], "title": p["title"],
               "persona": persona, "location": p.get("location"), "linkedin_url": p.get("linkedin"),
               "connection_degree": p.get("degree"), "profile_facts": p.get("facts"),
               "email": p.get("email") or None, "email_source": "import" if p.get("email") else None,
               "phone": p.get("phone") or None, "phone_source": "import" if p.get("phone") else None,
               "source": a.source or path.name}
        if hit:
            fills = {k: v for k, v in rec.items() if v and hit[k] in (None, "")}
            label = "fill " + ",".join(fills) if fills else "exists"
            if fills and a.commit:
                con.execute(f"UPDATE contacts SET {', '.join(k + '=?' for k in fills)}, updated_at=? WHERE id=?",
                            (*fills.values(), now(), hit["id"]))
        else:
            label = "new"
            if a.commit:
                rec = {k: v for k, v in rec.items() if v not in (None, "")}
                rec.update(created_at=now(), updated_at=now())
                con.execute(f"INSERT INTO contacts ({','.join(rec)}) VALUES ({','.join('?' * len(rec))})", tuple(rec.values()))
        n += label != "exists"
        print(f"  {label:<16} {p['first']} {p['last']:<20} {(p['title'] or '')[:45]:<45} "
              f"[{persona or 'no persona'}, {p.get('degree') or '?'}] -> {acc['name']}")
    if a.commit:
        con.commit()
    if skipped:
        print(f"\n{skipped} people had no matching account.")
    done(a.commit, n, "contact changes")


def cmd_add_contact(a) -> None:
    """One person (e.g. from a single pasted profile). Creates the account if needed."""
    con = connect()
    dom = norm_domain(a.domain)
    if suppressed(con, "linkedin", norm_li(a.linkedin)) or suppressed(con, "domain", dom):
        sys.exit("on the do-not-contact list")
    action, acc_id = upsert_account(con, {"name": a.company, "domain": dom, "source": a.source}, a.commit)
    acc = find_account(con, dom, None, a.company)
    persona = match_persona(a.title, persona_titles())
    hit = acc and con.execute("SELECT * FROM contacts WHERE account_id=? AND lower(first_name)=lower(?) AND lower(last_name)=lower(?)",
                              (acc["id"], a.first, a.last)).fetchone()
    print(f"  account {action:<8} {a.company} ({dom or 'no domain'})")
    print(f"  contact {'exists' if hit else 'new':<8} {a.first} {a.last}, {a.title or ''} [{persona or 'no persona'}]")
    if a.commit and not hit:
        acc_id = acc_id or (acc["id"] if acc else None)
        cur = con.execute("INSERT INTO contacts (account_id, first_name, last_name, title, persona, linkedin_url, connection_degree, "
                          "profile_facts, source, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                          (acc_id, a.first, a.last, a.title, persona, norm_li(a.linkedin), a.degree,
                           f"[profile {now()[:10]}] {a.facts.strip()}" if a.facts else None, a.source, now(), now()))
        con.commit()
        print(f"  contact id: {cur.lastrowid}")
    elif a.commit:
        con.commit()
        print(f"  contact id: {hit['id']}")
    done(a.commit, 0 if hit else 1, "contact")


def cmd_profile_facts(a) -> None:
    """Save facts from a person's full profile (pasted by the user) before a note is written.
    Appends a dated block; never deletes earlier facts."""
    con = connect()
    c = con.execute("SELECT * FROM contacts WHERE id=?", (a.contact_id,)).fetchone()
    if not c:
        sys.exit("no such contact")
    block = f"[profile {now()[:10]}] {a.facts.strip()}"
    new = (c["profile_facts"] + "\n" + block) if c["profile_facts"] else block
    print(f"  {c['first_name']} {c['last_name']}: {block[:150]}")
    if a.commit:
        con.execute("UPDATE contacts SET profile_facts=?, updated_at=? WHERE id=?", (new, now(), c["id"]))
        con.commit()
    done(a.commit, 1, "profile facts saved")


# ----------------------------------------------------------------------------- research verdicts
def read_jsonl(path: Path) -> list[tuple[int, dict | None, str | None]]:
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append((i, json.loads(line), None))
        except ValueError as e:
            out.append((i, None, f"not JSON ({e})"))
    return out


def cmd_apply_research(a) -> None:
    """Research lines from subagents -> accounts + signals. The whole file is refused on any error.

    {"company": "...", "domain": "x.com", "fit": "yes|no|unknown", "reason": "...",
     "country": "...", "size_employees": 120, "industry": "...", "description": "what they sell, to whom",
     "linkedin_url": "https://www.linkedin.com/company/...",
     "signal": {"type": "<signal name from directives/signals/>", "detail": "...", "source_url": "...", "observed_at": "2026-11-20"}}
    """
    con = connect()
    path = Path(a.file)
    rows, errs = [], []
    for i, v, err in read_jsonl(path):
        if err:
            errs.append(f"line {i}: {err}")
            continue
        fit = str(v.get("fit", "")).lower()
        fit = {"true": "yes", "false": "no"}.get(fit, fit)
        reason = (v.get("reason") or "").strip()
        if fit not in ("yes", "no", "unknown"):
            errs.append(f"line {i}: fit must be yes / no / unknown")
        if len(reason.split()) < 4:
            errs.append(f"line {i}: reason too short (say why, from evidence)")
        if fit == "yes" and not norm_domain(v.get("domain")):
            errs.append(f"line {i}: fit=yes needs a domain that was checked")
        if re.search(r"could not (load|open|read)|unreadable|timed? ?out|403|blocked", reason, re.I) and fit == "no":
            errs.append(f"line {i}: an unreadable site is 'unknown', never 'no'")
        sig = v.get("signal") or {}
        if sig and not sig.get("type"):
            errs.append(f"line {i}: signal needs a type")
        rows.append((i, v, fit, reason))
    if errs:
        print(f"{path.name} REFUSED, nothing written:\n  " + "\n  ".join(errs))
        sys.exit(1)
    n_acc = n_sig = 0
    for i, v, fit, reason in rows:
        dom = norm_domain(v.get("domain"))
        name = v.get("company") or v.get("employer") or dom
        if a.commit:
            con.execute("INSERT INTO verdicts (kind, subject, result, reason, source_file, created_at) VALUES (?,?,?,?,?,?)",
                        ("research", dom or name, json.dumps(v, ensure_ascii=False), reason, path.name, now()))
        if fit != "yes" and not a.store_all:
            print(f"  {fit:<8} {name[:40]:<40} {reason[:70]}")
            continue
        rec = {"name": name, "domain": dom, "country": v.get("country"), "size_employees": v.get("size_employees"),
               "industry": v.get("industry"), "description": v.get("description"),
               "linkedin_url": norm_li(v.get("linkedin_url")), "segment": a.segment, "fit": fit, "fit_reason": reason,
               "source": a.source or v.get("source") or path.stem}
        action, acc_id = upsert_account(con, rec, a.commit)
        # fit is a research judgment, not a human-entered value: the latest verdict sets it
        # (never on a disqualified account, which only a human may reopen)
        if action != "new":
            old = find_account(con, dom, None, name)
            if old and old["status"] != "disqualified" and (old["fit"], old["fit_reason"]) != (fit, reason):
                action = f"fit {old['fit']}->{fit}"
                if a.commit:
                    con.execute("UPDATE accounts SET fit=?, fit_reason=?, updated_at=? WHERE id=?", (fit, reason, now(), old["id"]))
        n_acc += action != "exists"
        sig = v.get("signal") or {}
        line = f"  {fit:<8} {name[:40]:<40} account:{action}"
        if sig and (acc_id or not a.commit):
            dup = acc_id and con.execute("SELECT 1 FROM signals WHERE account_id=? AND type=? AND coalesce(detail,'')=?",
                                         (acc_id, sig["type"], sig.get("detail") or "")).fetchone()
            if not dup:
                n_sig += 1
                line += f" + signal '{sig['type']}: {(sig.get('detail') or '')[:40]}'"
                if a.commit:
                    con.execute("INSERT INTO signals (account_id, type, detail, source_url, observed_at, created_at) VALUES (?,?,?,?,?,?)",
                                (acc_id, sig["type"], sig.get("detail"), sig.get("source_url"), sig.get("observed_at") or now()[:10], now()))
        print(line)
    if a.commit:
        con.commit()
    done(a.commit, n_acc + n_sig, f"changes ({n_acc} accounts, {n_sig} signals)")


def cmd_signals(a) -> None:
    con = connect()
    q = ("SELECT s.id, a.name, a.domain, s.type, s.detail, s.observed_at, s.active, s.source_url "
         "FROM signals s LEFT JOIN accounts a ON a.id=s.account_id")
    if a.active:
        q += " WHERE s.active=1"
    for r in con.execute(q + " ORDER BY s.observed_at DESC"):
        print(f"  #{r['id']:<4} {'ACTIVE' if r['active'] else 'closed'}  {r['observed_at'] or '':<10} {r['type']:<12} "
              f"{(r['name'] or '')[:30]:<30} {(r['detail'] or '')[:50]}")


def cmd_close_signal(a) -> None:
    con = connect()
    r = con.execute("SELECT * FROM signals WHERE id=?", (a.id,)).fetchone()
    if not r:
        sys.exit("no such signal")
    print(f"  close #{r['id']} {r['type']}: {r['detail']}")
    if a.commit:
        con.execute("UPDATE signals SET active=0, checked_at=? WHERE id=?", (now(), a.id))
        con.commit()
    done(a.commit, 1, "signal closed")


# ----------------------------------------------------------------------------- drafts (LinkedIn connect notes and DMs)
DEFAULT_RULES = {
    "linkedin-connect": {"max_chars": 200, "must_start": "Hi {first}, ",
                         "banned": ["offer", "demo", "call", "meeting", "price", "pricing", "free", "discount", "congrat"]},
    "linkedin-dm": {"max_chars": 600, "must_start": "", "banned": ["congrat", "guarantee", "act now"]},
}


def load_rules(kind: str) -> dict:
    """Defaults, overridden by a '## Rules (checked by gtm.py)' block in the channel's directive:
    lines like `max_chars: 200` or `banned: offer, demo, call`."""
    rules = json.loads(json.dumps(DEFAULT_RULES[kind]))
    directive = WS / "directives" / "linkedin.md"
    if not directive.exists():
        return rules
    text = directive.read_text(encoding="utf-8")
    m = re.search(r"## Rules \(checked by gtm\.py\)(.*?)(?:\n## |\Z)", text, re.S)
    if not m:
        return rules
    sub = re.search(rf"### {re.escape(kind)}\s*\n(.*?)(?:\n### |\Z)", m.group(1), re.S)
    for line in (sub.group(1) if sub else "").splitlines():
        mm = re.match(r"^\s*[-*]?\s*`?([a-z_]+)`?\s*:\s*(.+)$", line.strip())
        if not mm:
            continue
        k, val = mm.group(1), mm.group(2).strip().strip("`")
        if k in ("max_chars", "max_words"):
            rules[k] = int(re.sub(r"\D", "", val) or rules.get(k, 0))
        elif k == "banned":
            rules[k] = [w.strip().lower() for w in val.split(",") if w.strip()]
        elif k == "must_start":
            rules[k] = val.strip('"')
    return rules


def check_draft(v: dict, contact) -> list[str]:
    kind = v.get("kind") or "linkedin-connect"
    if kind not in DEFAULT_RULES:
        return [f"kind must be one of {', '.join(DEFAULT_RULES)}"]
    r = load_rules(kind)
    body = (v.get("body") or "").strip()
    errs = []
    first = (contact["first_name"] or "").split(" ")[0] if contact else ""
    if not body:
        return ["empty body"]
    if r.get("must_start") and not body.startswith(r["must_start"].replace("{first}", first)):
        errs.append(f"must start with '{r['must_start'].replace('{first}', first)}'")
    if r.get("max_chars") and len(body) > r["max_chars"]:
        errs.append(f"{len(body)} characters (max {r['max_chars']})")
    if r.get("max_words") and len(body.split()) > r["max_words"]:
        errs.append(f"{len(body.split())} words (max {r['max_words']})")
    for w in r.get("banned", []):
        if re.search(rf"\b{re.escape(w)}", body, re.I):
            errs.append(f"banned word: {w!r}")
    if "—" in body or "–" in body:
        errs.append("long dash (reads machine-written)")
    if "{" in body or "}" in body:
        errs.append("unfilled placeholder")
    if not (v.get("basis") or "").strip():
        errs.append("no basis: which fact about them is this based on?")
    return errs


def load_drafts(con, path: Path):
    good, errs = [], []
    for i, v, err in read_jsonl(path):
        if err:
            errs.append(f"line {i}: {err}")
            continue
        c = con.execute("SELECT * FROM contacts WHERE id=?", (v.get("contact_id"),)).fetchone()
        if not c:
            errs.append(f"line {i}: no contact with id {v.get('contact_id')}")
            continue
        bad = check_draft(v, c)
        if bad:
            errs.append(f"line {i} ({c['first_name']} {c['last_name']}): " + "; ".join(bad))
        else:
            good.append((c, v))
    return good, errs


def cmd_check_drafts(a) -> None:
    con = connect()
    good, errs = load_drafts(con, Path(a.file))
    for c, v in good:
        print(f"  ok   {c['first_name']} {c['last_name']:<18} ({len(v['body'])} chars) {v['body'][:110]}")
    for e in errs:
        print(f"  FAIL {e}")
    print(f"\n{len(good)} valid, {len(errs)} to fix")
    sys.exit(1 if errs else 0)


def cmd_apply_drafts(a) -> None:
    con = connect()
    good, errs = load_drafts(con, Path(a.file))
    if errs:
        print("REFUSED, nothing written (fix every line first):\n  " + "\n  ".join(errs))
        sys.exit(1)
    for c, v in good:
        kind = v.get("kind") or "linkedin-connect"
        channel = "linkedin"
        print(f"  {kind:<17} {c['first_name']} {c['last_name']}")
        if a.commit:
            con.execute("UPDATE drafts SET status='dropped' WHERE contact_id=? AND kind=? AND status='draft'", (c["id"], kind))
            con.execute("INSERT INTO drafts (contact_id, channel, kind, subject, body, basis, created_at) VALUES (?,?,?,?,?,?,?)",
                        (c["id"], channel, kind, v.get("subject"), v["body"].strip(), v["basis"].strip(), now()))
    if a.commit:
        con.commit()
    done(a.commit, len(good), "drafts saved")


def cmd_log_touch(a) -> None:
    if a.channel not in CHANNELS or a.kind not in TOUCH_KINDS:
        sys.exit(f"channel in {sorted(CHANNELS)}, kind in {sorted(TOUCH_KINDS)}")
    con = connect()
    c = con.execute("SELECT * FROM contacts WHERE id=?", (a.contact_id,)).fetchone()
    if not c:
        sys.exit("no such contact")
    print(f"  {a.channel}/{a.kind} -> {c['first_name']} {c['last_name']} {('(' + a.outcome + ')') if a.outcome else ''}")
    if a.commit:
        con.execute("INSERT INTO touches (contact_id, channel, kind, body, outcome, at, created_at) VALUES (?,?,?,?,?,?,?)",
                    (c["id"], a.channel, a.kind, a.body, a.outcome, a.at or now(), now()))
        if a.kind in ("invite", "message", "email"):
            con.execute("UPDATE drafts SET status='sent' WHERE contact_id=? AND channel=? AND status='draft'",
                        (c["id"], a.channel))
        con.commit()
    done(a.commit, 1, "touch logged")


# ----------------------------------------------------------------------------- do-not-contact list
def cmd_suppress(a) -> None:
    con = connect()
    val = norm_domain(a.value) if a.kind == "domain" else (norm_li(a.value) if a.kind == "linkedin" else a.value.strip())
    print(f"  do-not-contact: {a.kind} {val} ({a.reason})")
    if a.commit:
        con.execute("INSERT OR IGNORE INTO suppression (kind, value, reason, created_at) VALUES (?,?,?,?)",
                    (a.kind, val, a.reason, now()))
        con.commit()
    done(a.commit, 1, "suppression entry")


# ----------------------------------------------------------------------------- pipeline
def pipeline_data(con) -> dict:
    d = {}
    d["drafts_ready"] = con.execute("""SELECT d.id, d.kind, c.id AS cid, c.first_name, c.last_name, a.name AS company, d.body
        FROM drafts d JOIN contacts c ON c.id=d.contact_id LEFT JOIN accounts a ON a.id=c.account_id
        WHERE d.status='draft' ORDER BY d.created_at""").fetchall()
    d["accepted_no_dm"] = con.execute("""SELECT c.id AS cid, c.first_name, c.last_name, a.name AS company, max(t.at) AS at
        FROM touches t JOIN contacts c ON c.id=t.contact_id LEFT JOIN accounts a ON a.id=c.account_id
        WHERE t.channel='linkedin' AND t.kind='accepted'
          AND NOT EXISTS (SELECT 1 FROM touches m WHERE m.contact_id=c.id AND m.channel='linkedin' AND m.kind='message' AND m.at>=t.at)
        GROUP BY c.id""").fetchall()
    d["invites_stale"] = con.execute("""SELECT c.id AS cid, c.first_name, c.last_name, a.name AS company, max(t.at) AS at
        FROM touches t JOIN contacts c ON c.id=t.contact_id LEFT JOIN accounts a ON a.id=c.account_id
        WHERE t.channel='linkedin' AND t.kind='invite'
          AND NOT EXISTS (SELECT 1 FROM touches x WHERE x.contact_id=c.id AND x.kind IN ('accepted','withdrawn','reply'))
        GROUP BY c.id HAVING julianday('now') - julianday(max(t.at)) > 7""").fetchall()
    d["replies"] = con.execute("""SELECT c.id AS cid, c.first_name, c.last_name, a.name AS company, t.at, t.body
        FROM touches t JOIN contacts c ON c.id=t.contact_id LEFT JOIN accounts a ON a.id=c.account_id
        WHERE t.kind='reply' AND julianday('now') - julianday(t.at) <= 14 ORDER BY t.at DESC""").fetchall()
    d["new_signals"] = con.execute("""SELECT s.id, a.name AS company, s.type, s.detail, s.observed_at FROM signals s
        LEFT JOIN accounts a ON a.id=s.account_id WHERE s.active=1 AND julianday('now') - julianday(s.created_at) <= 7
        ORDER BY s.created_at DESC""").fetchall()
    d["fit_no_people"] = con.execute("""SELECT a.id, a.name, a.domain FROM accounts a WHERE a.fit='yes' AND a.status!='disqualified'
        AND NOT EXISTS (SELECT 1 FROM contacts c WHERE c.account_id=a.id)""").fetchall()
    d["old_signals"] = con.execute("""SELECT s.id, a.name AS company, s.detail, s.observed_at FROM signals s
        LEFT JOIN accounts a ON a.id=s.account_id
        WHERE s.active=1 AND julianday('now') - julianday(coalesce(s.checked_at, s.observed_at)) > 30""").fetchall()
    return d


SECTIONS = [
    ("replies", "Replies in the last 14 days: answer these first"),
    ("accepted_no_dm", "Accepted, no follow-up DM yet"),
    ("drafts_ready", "Drafts ready to send"),
    ("new_signals", "New signals this week"),
    ("fit_no_people", "Fit accounts without people: find 1-2 contacts"),
    ("invites_stale", "Invites open more than 7 days: nudge once, withdraw after 3 weeks"),
    ("old_signals", "Signals older than 30 days: re-check they are still live"),
]


def row_text(key: str, r) -> str:
    if key == "drafts_ready":
        return f"#{r['cid']} {r['first_name']} {r['last_name']} ({r['company']}): {r['kind']}"
    if key in ("new_signals", "old_signals"):
        return f"{r['company']}: {r['detail']} ({r['observed_at']})"
    if key == "fit_no_people":
        return f"{r['name']} ({r['domain']})"
    return f"#{r['cid']} {r['first_name']} {r['last_name']} ({r['company']}) {str(r['at'])[:10]}"


def cmd_pipeline(a) -> None:
    con = connect()
    d = pipeline_data(con)
    for key, title in SECTIONS:
        rows = d[key]
        print(f"\n{title} [{len(rows)}]")
        for r in rows[:15]:
            print("  " + row_text(key, r))
    if a.html:
        parts = [f"<section><h2>{html.escape(t)} <span>{len(d[k])}</span></h2><ul>" +
                 "".join(f"<li>{html.escape(row_text(k, r))}</li>" for r in d[k]) + "</ul></section>"
                 for k, t in SECTIONS]
        page = ("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
                "<title>Pipeline today</title><style>body{font:15px/1.5 system-ui;max-width:860px;margin:2rem auto;padding:0 1rem;"
                "color:#1d1d1f;background:#fafaf8}h1{font-size:1.6rem}h2{font-size:1.05rem;margin-top:1.6rem}"
                "h2 span{background:#e8e6df;border-radius:9px;padding:0 .5rem;font-size:.85rem}li{margin:.2rem 0}"
                "@media(prefers-color-scheme:dark){body{background:#161615;color:#eee}h2 span{background:#333}}</style>"
                f"<h1>Pipeline, {dt.date.today().isoformat()}</h1>" + "".join(parts))
        Path(a.html).parent.mkdir(parents=True, exist_ok=True)
        Path(a.html).write_text(page, encoding="utf-8")
        print(f"\nHTML report -> {a.html}")


def cmd_query(a) -> None:
    if not DB_PATH.exists():
        sys.exit("no database")
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(a.sql).fetchall()
    except sqlite3.Error as e:
        sys.exit(f"SQL error: {e}")
    if not rows:
        print("(no rows)")
        return
    keys = rows[0].keys()
    print(" | ".join(keys))
    for r in rows[: a.limit]:
        print(" | ".join("" if r[k] is None else str(r[k])[:60] for k in keys))
    if len(rows) > a.limit:
        print(f"... {len(rows) - a.limit} more")


# ----------------------------------------------------------------------------- your own company
def cmd_set_company(a) -> None:
    dom = norm_domain(a.domain)
    if not dom:
        sys.exit("give a domain, e.g. --domain example.com")
    con = connect()
    print(f"  own company: domain={dom}" + (f", name={a.name}" if a.name else ""))
    if a.commit:
        con.execute("INSERT OR REPLACE INTO meta VALUES ('own_domain', ?)", (dom,))
        if a.name:
            con.execute("INSERT OR REPLACE INTO meta VALUES ('own_name', ?)", (a.name.strip(),))
        con.commit()
    done(a.commit, 1, "company setting")


# ----------------------------------------------------------------------------- ui (read-only local view)
UI_PAGE = PLUGIN_ROOT / "ui" / "index.html"
SITES = WS / ".tmp" / "sites"
# The page may only talk to this server: no external scripts, images or requests.
PAGE_CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; "
            "img-src 'self'; connect-src 'self'")
STATUS_MARK = {"✅": "confirmed", "🟡": "check", "⬜": "missing"}


def _heading(line: str) -> str:
    """'## 1. What you sell' / '### 🙋 Who they are' -> 'What you sell' / 'Who they are'."""
    h = re.sub(r"^#+\s*", "", line.strip())
    return re.sub(r"^[^\w(]*(\d+\.\s*)?", "", h).strip()


def doc_params(path: Path) -> list[dict]:
    """Every row of a 'Parameter | Value' table, with its persona (if any), its group heading,
    and its status mark (✅ 🟡 ⬜). The playbook is the source; nothing is stored twice."""
    if not path.exists():
        return []
    out, header, persona, group = [], None, None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        m = re.match(r"^##\s+Persona:\s*(.+)$", t)
        if m:
            persona, group = _plain(m.group(1)), None
        elif t.startswith("### "):
            group = _heading(t)
        elif t.startswith("## "):
            persona, group = None, _heading(t)
        if not t.startswith("|"):
            header = None
            continue
        raw = [c.strip() for c in t.strip("|").split("|")]
        cells = [_plain(c) for c in raw]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(t.replace("|", "").strip()) <= set("-: "):
            continue
        if header and header[0] == "parameter" and "value" in header:
            row = dict(zip(header, cells))
            conf_raw = dict(zip(header, raw)).get("confidence", "")
            value = row.get("value", "")
            status = next((v for k, v in STATUS_MARK.items() if k in conf_raw), "")
            if not value or value.lower() in EMPTY:
                status, value = "missing", ""
            elif status in ("", "missing"):
                status = "check"
            out.append({"persona": persona, "group": group, "parameter": row.get("parameter", ""),
                        "value": value, "source": row.get("source", ""), "status": status})
    return out


def doc_bullets(path: Path, heading_word: str) -> list[str]:
    """The '- ...' lines under the heading that contains heading_word (placeholders skipped)."""
    if not path.exists():
        return []
    out, inside = [], False
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        if t.startswith("#"):
            inside = heading_word.lower() in t.lower()
            continue
        if inside and t.startswith("- "):
            item = t[2:].strip()
            if item and not re.match(r"^_?\(e\.g\.", item):
                out.append(_plain(item))
    return out


def about_me() -> dict:
    """The owner's background from directives/linkedin.md (used in every connect note)."""
    path = WS / "directives" / "linkedin.md"
    if not path.exists():
        return {"facts": [], "now": ""}
    facts, header, now = [], None, ""
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.strip()
        m = re.match(r"^\*\*Who I am now\*\*[^:]*:\s*(.*)$", t)
        if m:
            v = _plain(m.group(1))
            now = "" if v.lower().startswith("e.g.") else v
        if not t.startswith("|"):
            header = None
            continue
        cells = [_plain(c) for c in t.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(t.replace("|", "").strip()) <= set("-: "):
            continue
        if header and header[0].startswith("fact about me") and cells[0]:
            facts.append({"fact": cells[0], "fits": cells[1] if len(cells) > 1 else ""})
    return {"facts": facts, "now": now}


def logo_file(domain: str | None) -> Path | None:
    if not domain or not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", domain):
        return None
    return next(iter(sorted((SITES / domain).glob("logo.*"))), None) if (SITES / domain).is_dir() else None


def nice_name(domain: str, facts: dict) -> str:
    """A company name from what the site says about itself, else from the domain."""
    org = facts.get("organization_schema") or {}
    for v in (org.get("name"), facts.get("site_name")):
        if isinstance(v, str) and 1 < len(v.strip()) <= 60:
            return v.strip()
    stem = re.sub(r"[^a-z0-9]", "", domain.split(".")[0])
    parts = [x.strip() for x in re.split(r"\s[|\-–—·:]\s", facts.get("title") or "") if x.strip()]
    for part in parts:
        if re.sub(r"[^a-z0-9]", "", part.lower()) in (stem, stem.replace("the", "")) or \
           (len(part) <= 40 and stem and stem in re.sub(r"[^a-z0-9]", "", part.lower())):
            return part
    return domain.split(".")[0].replace("-", " ").title()


def own_company(con) -> dict | None:
    meta = dict(con.execute("SELECT key, value FROM meta").fetchall())
    dom = meta.get("own_domain")
    if not dom:
        try:
            dom = norm_domain(json.loads((WS / ".tmp" / "guide.json").read_text()).get("domain"))
        except (OSError, ValueError, AttributeError):
            dom = None
    if not dom:
        return None
    facts = {}
    try:
        facts = json.loads((SITES / dom / "facts.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return {
        "domain": dom, "name": meta.get("own_name") or nice_name(dom, facts),
        "headline": facts.get("headline", ""), "description": facts.get("description", ""),
        "linkedin": facts.get("company_linkedin"), "languages": facts.get("languages", []),
        "pages_read": facts.get("pages_read"), "read_at": facts.get("read_at"),
        "readable": facts.get("readable"), "logo": bool(logo_file(dom)),
    }


def profile_data(con) -> dict:
    d = WS / "directives"
    return {
        "company": own_company(con),
        "icp": doc_params(d / "icp.md"),
        "fit_rule": doc_bullets(d / "icp.md", "fit rule"),
        "personas": doc_params(d / "personas.md"),
        "me": about_me(),
    }


def ui_data() -> dict:
    """Everything the page shows, from a read-only connection. Plain JSON, no timestamps,
    so the page can compare two answers and redraw only when the data changed."""
    con = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = lambda sql: [dict(r) for r in con.execute(sql).fetchall()]
    try:
        pipe = pipeline_data(con)
        return {
            "workspace": WS.name,
            "accounts": rows("SELECT * FROM accounts ORDER BY coalesce(updated_at, created_at) DESC, id DESC"),
            "contacts": rows("""SELECT id, account_id, first_name, last_name, title, persona, location, linkedin_url,
                connection_degree, profile_facts, email, email_status, email_source, phone, phone_type,
                source, created_at, updated_at FROM contacts ORDER BY id DESC"""),
            "signals": rows("SELECT * FROM signals ORDER BY coalesce(observed_at, created_at) DESC, id DESC"),
            "drafts": rows("SELECT id, contact_id, channel, kind, subject, body, created_at FROM drafts "
                           "WHERE status='draft' ORDER BY id"),
            "touches": rows("SELECT id, contact_id, channel, kind, outcome, at FROM touches ORDER BY at, id"),
            "pipeline": [{"key": k, "title": t, "rows": [row_text(k, r) for r in pipe[k]]} for k, t in SECTIONS],
            "profile": profile_data(con),
            "logos": sorted(p.parent.name for p in SITES.glob("*/logo.*")) if SITES.is_dir() else [],
        }
    finally:
        con.close()


def cmd_ui(a) -> None:
    import http.server
    import webbrowser

    if not DB_PATH.exists():
        sys.exit("No database here. Run `init` in your workspace folder first.")
    if not UI_PAGE.exists():
        sys.exit(f"UI page missing: {UI_PAGE}")
    page = UI_PAGE.read_bytes()

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, code: int, body: bytes, ctype: str, csp: str = PAGE_CSP) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", csp)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            # Only answer requests addressed to this machine (blocks DNS-rebinding tricks).
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                return self._send(403, b"forbidden", "text/plain")
            path = self.path.split("?")[0]
            if path in ("/", "/index.html"):
                return self._send(200, page, "text/html; charset=utf-8")
            if path == "/api/data":
                try:
                    body = json.dumps(ui_data(), default=str).encode()
                except sqlite3.Error as e:
                    return self._send(500, json.dumps({"error": str(e)}).encode(), "application/json")
                return self._send(200, body, "application/json")
            if path.startswith("/logo/"):
                f = logo_file(path[len("/logo/"):].lower())
                if f:
                    ctype = {"svg": "image/svg+xml", "png": "image/png", "jpg": "image/jpeg", "gif": "image/gif",
                             "webp": "image/webp", "ico": "image/x-icon"}.get(f.suffix[1:], "application/octet-stream")
                    # a logo is a file from someone else's website: no scripts, ever
                    return self._send(200, f.read_bytes(), ctype, "default-src 'none'; style-src 'unsafe-inline'; sandbox")
            self._send(404, b"not found", "text/plain")

        def log_message(self, *args) -> None:  # keep the terminal quiet
            pass

    server = None
    for port in range(a.port, a.port + 20):
        try:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        sys.exit(f"No free port between {a.port} and {a.port + 19}.")
    # Served on 127.0.0.1 only; "localhost" is the friendlier name for the same address.
    url = f"http://localhost:{server.server_address[1]}/"
    print(f"Live view of {DB_PATH.relative_to(WS)} (read-only): {url}")
    print("It refreshes by itself. Stop with Ctrl+C.", flush=True)
    if not a.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


# ----------------------------------------------------------------------------- CLI
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    p = sub.add_parser("profile-check"); p.add_argument("kind", choices=["icp", "persona"]); p.set_defaults(fn=cmd_profile_check)
    p = sub.add_parser("import-contacts"); p.add_argument("--file", required=True); p.add_argument("--account-domain")
    p.add_argument("--source"); p.add_argument("--skip", nargs="*", default=[]); p.add_argument("--commit", action="store_true")
    p.set_defaults(fn=cmd_import_contacts)
    p = sub.add_parser("add-contact"); p.add_argument("--company", required=True); p.add_argument("--domain")
    p.add_argument("--first", required=True); p.add_argument("--last", default=""); p.add_argument("--title")
    p.add_argument("--linkedin"); p.add_argument("--degree"); p.add_argument("--facts", help="profile facts the note may use")
    p.add_argument("--source", default="pasted profile"); p.add_argument("--commit", action="store_true")
    p.set_defaults(fn=cmd_add_contact)
    p = sub.add_parser("profile-facts"); p.add_argument("--contact-id", type=int, required=True)
    p.add_argument("--facts", required=True, help="the facts from the full profile a note may use")
    p.add_argument("--commit", action="store_true"); p.set_defaults(fn=cmd_profile_facts)
    p = sub.add_parser("apply-research"); p.add_argument("--file", required=True); p.add_argument("--source")
    p.add_argument("--segment"); p.add_argument("--store-all", action="store_true", help="also store fit=no/unknown accounts")
    p.add_argument("--commit", action="store_true"); p.set_defaults(fn=cmd_apply_research)
    p = sub.add_parser("signals"); p.add_argument("--active", action="store_true"); p.set_defaults(fn=cmd_signals)
    p = sub.add_parser("close-signal"); p.add_argument("--id", type=int, required=True); p.add_argument("--commit", action="store_true")
    p.set_defaults(fn=cmd_close_signal)
    p = sub.add_parser("check-drafts"); p.add_argument("--file", required=True); p.set_defaults(fn=cmd_check_drafts)
    p = sub.add_parser("apply-drafts"); p.add_argument("--file", required=True); p.add_argument("--commit", action="store_true")
    p.set_defaults(fn=cmd_apply_drafts)
    p = sub.add_parser("log-touch"); p.add_argument("--contact-id", type=int, required=True); p.add_argument("--channel", required=True)
    p.add_argument("--kind", required=True); p.add_argument("--body"); p.add_argument("--outcome"); p.add_argument("--at")
    p.add_argument("--commit", action="store_true"); p.set_defaults(fn=cmd_log_touch)
    p = sub.add_parser("suppress"); p.add_argument("--kind", required=True, choices=["email", "phone", "domain", "linkedin"])
    p.add_argument("--value", required=True); p.add_argument("--reason", required=True); p.add_argument("--commit", action="store_true")
    p.set_defaults(fn=cmd_suppress)
    p = sub.add_parser("pipeline"); p.add_argument("--html"); p.set_defaults(fn=cmd_pipeline)
    p = sub.add_parser("query"); p.add_argument("sql"); p.add_argument("--limit", type=int, default=50); p.set_defaults(fn=cmd_query)
    p = sub.add_parser("set-company"); p.add_argument("--domain", required=True); p.add_argument("--name")
    p.add_argument("--commit", action="store_true"); p.set_defaults(fn=cmd_set_company)
    p = sub.add_parser("ui"); p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-open", action="store_true", help="do not open the browser"); p.set_defaults(fn=cmd_ui)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
