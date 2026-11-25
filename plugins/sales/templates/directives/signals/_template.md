# 📡 Signal: <name>

> **In one line:** they <do something public>, which usually means <pain>, so <my offer> helps now.

| At a glance | |
|---|---|
| **Type in the database** | `<name>` (lowercase, no spaces) |
| **Source** | <job board / company website page / news / event list / LinkedIn search / CSV> |
| **How often** | <daily / weekly / per event> |
| **Expires after** | <N> days |
| **Status** | 🧪 testing |

---

## 1. What it means

| | |
|---|---|
| **What we observe** | <the public, dated event> |
| **What it usually means** | <the pain or need behind it> |
| **Why my offer helps then** | <how exactly> |
| **Applies to** | <ICP segment / persona> |

## 2. How we collect it

<The user pastes results / exports a CSV / gives a list of URLs; Claude reads company sites
with site_read.py.> Never scrape LinkedIn or sites that forbid it.

## 3. How we detect it (rules, no AI)

| ✅ Keep if | ❌ Drop if |
|---|---|
| <keywords, titles, page types, dates> | <recruiters, big groups, wrong roles, duplicates, older than N days> |

## 4. How we verify it (research)

The research subagent answers these from evidence, with a link:

1. <Is the event real and recent?>
2. <Does it really mean the pain for this company?>
3. <Does the company fit the ICP fit rule?>

## 5. What we store

| Field | Content |
|---|---|
| `detail` | <e.g. the ad title, the event name, the new leader's name and title> |
| `source_url` | <the page that proves it> |
| `observed_at` | <the date of the event> |

## 6. The first line it gives you

> "<e.g. I saw you are hiring a second bookkeeper.>"

Then the message playbooks (`linkedin.md`, `cold_email.md`) take over.

---

## 📓 Learnings

| Date | Collected → kept → fits | Main noise | What we changed |
|---|---|---|---|
| | | | |
