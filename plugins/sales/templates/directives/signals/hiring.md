# 📡 Signal: hiring *(worked example)*

> **In one line:** they post a job ad for a role whose work my offer removes, which means
> that work is growing faster than the team, so my offer helps right now.
>
> A job ad is a company telling the world it has a problem.

| At a glance | |
|---|---|
| **Type in the database** | `hiring` |
| **Source** | LinkedIn Jobs, other job boards, company careers pages |
| **How often** | Daily or weekly |
| **Expires after** | 30 days (re-check; close it when the ad is gone) |
| **Status** | 🧪 example |

---

## 🗺️ The map: which roles mean a pain I solve

Fill in your own rows. Claude proposes them from your ICP triggers.

| They hire (role) | Which means (pain) | So my offer helps by | Search words |
|---|---|---|---|
| | | | |

<details>
<summary><b>Example rows from other businesses</b> (click to open)</summary>

| They hire (role) | Which means (pain) | So my offer helps by | Search words |
|---|---|---|---|
| Bookkeeper | Admin work grows faster than the team | Automating invoice and expense flows | bookkeeper, accounts payable |
| Social media manager | They need content but have nobody | A done-for-you content system | social media manager, content creator |
| Customer support agent | Support requests grow faster than the team | A help center and chat that answer common questions | support agent, customer service |
| Office manager | Scheduling and admin overwhelm the founders | Automated booking and admin workflows | office manager, administrative assistant |

</details>

---

## 1. How we collect it

1. Search the **search words** on LinkedIn Jobs (or any job board).
2. Filter **Past 24 hours** or **Past week**, and your region.
3. Copy the results pages 1 to 3 and paste them into the chat. Later pages drift off-topic.

Never scrape job boards with a script.

## 2. How we detect it (rules, no AI)

| ✅ Keep if | ❌ Drop if |
|---|---|
| The job title matches the search words of a map row | A recruiter or staffing agency posts for a hidden client |
| | A large group outside your ICP size (a local office counts as the group) |
| | The same title means a different job (e.g. "consultant" in sales vs. in IT) |
| | The company is already in your database |

**Recruiters and job platforms to skip** (add names as you meet them, lowercase):
`recruiter, staffing, personnel, talent, headhunt, executive search, jobs`

## 3. How we verify it (research)

1. Is the employer a real company with its own website, not a recruiter? Is the ad on its
   careers page? (Use that link if found.)
2. Does the role really match the pain in the map row?
3. Does the company fit the ICP fit rule (size, type, region)?

## 4. What we store

| Field | Content |
|---|---|
| `detail` | The ad title |
| `source_url` | The ad link, if found |
| `observed_at` | The posting date |

> **Stronger signal:** an ad posted again and again for months. The problem is hard to
> solve by hiring.

## 5. The first line it gives you

> "I saw you are hiring a <role>."

Then one sentence on why that usually means <pain>.

---

## 📓 Learnings

| Date | Ads pasted → kept → fits | Main noise | What we changed |
|---|---|---|---|
| | | | |
