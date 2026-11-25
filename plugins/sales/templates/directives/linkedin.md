# 💬 LinkedIn: connect first, then follow up

> **Two steps, never mixed.**
> **1. Connect note:** earn the connection. No pitch, no offer: a true, specific
> compliment and real common ground.
> **2. Follow-up DM:** only after they accept. Now you bring the signal and a small,
> useful offer.

**Why this order:** a pitch inside a connection request gets fewer accepts, and a declined
request closes the channel for months. A note that shows you looked at *them* gets
accepted far more often.

---

## 🙋 About me (used in every note)

Fill this in once (the `persona` step asks you). Claude picks the **one** fact that truly
overlaps with each person.

| Fact about me | Fits people who… |
|---|---|
| | |
| | |

**Who I am now** (the same in every note): _e.g. "now a founder building AI for small agencies"_

---

## 1. The connect note

> 📋 **Always start from the full profile.** A line in a search list (name, title, years
> in role) is not enough. Open the person's profile, copy all of it (About, Experience,
> Activity), paste it to Claude, and only then write the note. One person at a time.

**Shape**

> Hi {first name}, **{3 to 6 words about them}**. **{true common ground}**, **{who I am now}**, thought I'd connect.

**What to appreciate, best first**

| # | Look for | Example opener |
|---|---|---|
| 1 | A post from the last 2 to 3 weeks with their own opinion or story | "loved your take on hiring juniors" |
| 2 | Their work now: what they build, run or fix | "loved your work on clean energy storage" |
| 3 | A value they show | "loved your focus on craft" |
| 4 | An unusual path (only if truly unusual) | "loved your shop floor roots" |

**Good and bad**

| ✅ Do | ❌ Avoid |
|---|---|
| Say it in 3 to 6 of **your own** words | Quoting their headline or listing facts |
| Write about the **person** | Writing only about their company |
| Use what is on their profile **now** | Old jobs from years ago |
| Say "also" only if it is visible on their profile | Invented common ground |
| Keep it warm and plain | "Congrats on the new role" from a stranger |

**Example:** _too detailed_ "loved your journey from toolmaker in Germany to leading
components sales in the US" → _better_ "loved your shop floor roots".

---

## 2. The follow-up DM (after they accept)

Send it 1 to 3 days after they accept.

| Part | What it does | Example |
|---|---|---|
| Thanks | One short line | "Thanks for connecting, Ana." |
| What I saw | The signal, specific | "I saw Northwind is hiring a bookkeeper." |
| Why it matters | One sentence, "usually", no invented numbers | "That usually means admin work grows faster than the team." |
| Small offer | Something you make for them, quick to judge, with a clean exit | "I could record a 3 minute video … If not useful, just ignore this." |
| Easy reply | A yes/no question | "Want it?" |

No reply after 5 to 7 days: one short nudge, or switch to email. Never both channels on the same day.

**Pacing:** 1 to 2 people per company at a time (different teams), stay well under
LinkedIn's weekly invite limit, and withdraw invites still open after about 3 weeks.

---

## Rules (checked by gtm.py)

Every note and DM is checked against these lines before it is saved. Edit them to match
your style; keep the `key: value` format.

### linkedin-connect
- max_chars: 200
- must_start: Hi {first}, 
- banned: offer, demo, call, meeting, price, pricing, free, discount, congrat

### linkedin-dm
- max_chars: 600
- banned: congrat, guarantee, act now

---

## 📓 Learnings

| Date | Note style | Sent → accepted | What we changed |
|---|---|---|---|
| | | | |
