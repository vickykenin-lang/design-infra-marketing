# AURA Handover Guide — for Vicky

Written 2026-08-17 by Dr. Victor, as part of Day 7 (full dress rehearsal +
handover). This is the one document to read if you want the whole picture
of what AURA is, what she does on her own, and what only you can do.

## What AURA is

AURA is the AI CEO of Sales & Marketing for **Design Infra** (your turnkey
interior company, Delhi NCR → pan-India metros). She runs entirely inside
this GitHub repo — no app to install, nothing running on your computer.
Her heartbeat is GitHub Actions (free tier), her memory is the JSON files
in `data/`, and her public face is the dashboard at
`https://docs.designinfra.in/` (bilingual, Hindi by default).

## What she does automatically, on a schedule, with no input from you

- **Every 3 hours**: heartbeat — checks for your GitHub issues (messages,
  approvals, kill switch, new leads), updates dashboard stats.
- **Daily, 19:00 IST**: publishes the day's scheduled Instagram post (and
  Pinterest pin once you add the Pinterest secrets — see below).
- **Weekly, Friday morning**: researches real, free, licensed interior
  photos; re-renders post cards; runs two independent AI reviews (an
  interior-designer/marketer persona and an ordinary-homeowner persona)
  before anything goes in the queue.
- **Instantly on a GitHub issue**: she reacts the moment you open an issue
  with certain titles (see the command list below) — you don't have to
  wait for the 3-hour heartbeat for these.

## Dress rehearsal — what was actually tested live today (2026-08-17)

Not just "the code exists" — these were run for real, with real GitHub
issues, and the results verified on the live dashboard:

1. **Kill switch** (issue #30): opened a real "KILL SWITCH" issue →
   dashboard showed "Paused (kill switch)" within one heartbeat cycle →
   manually resumed per the documented process. Confirmed working
   end-to-end.
2. **New lead intake** (issue #31): opened a real "NEW LEAD" issue with
   test data → heartbeat scored it 100/100 (HOT), posted a bilingual
   comment explaining the score, closed the issue, and the lead appeared
   correctly on the live dashboard's Leads card (count, weekly count,
   average score) within the same run. Confirmed working end-to-end.
3. **Dashboard data pipeline**: confirmed `leads.json`,
   `lead_daily_report.json`, and `status.json` all update correctly and
   the dashboard reflects them after a hard refresh.

Not re-tested today (already proven working in earlier days and unchanged
since): Instagram publishing (1 real post live), the weekly content-review
pipeline, the bilingual voice listen/speak dashboard feature.

## Your one-tap controls (all via the dashboard)

Every button below opens a pre-filled GitHub issue — you just add any
details and hit Create. AURA reacts within minutes (issue-triggered) or at
worst the next 3-hour heartbeat.

| Button | What it does |
|---|---|
| Send a message | Appends to her inbox; she reads it every heartbeat |
| Approve / Reject a post | Updates that post's status in the queue |
| Kill switch | Pauses ALL publishing instantly — nothing else stops |
| Log a new lead | Scores a lead (phone/WhatsApp/in-person) into the system |

You can also just open a GitHub issue directly (Issues tab → New issue)
with the matching title if you'd rather not go through the dashboard.

## What only you can do (AURA and I cannot create accounts or handle credentials)

**Blocking real leads from reaching you right now:**
1. Open `leads.html`, find the `CONFIG` block near the top, and replace
   the placeholder WhatsApp number (`91XXXXXXXXXX`) and email
   (`leads@designinfra.in`) with Design Infra's real ones. Until this is
   done, don't share the `leads.html` link publicly — the form works, but
   hands off to placeholder contacts.

**Blocking Pinterest publishing:**
2. Add `PIN_ACCESS_TOKEN` and `PIN_BOARD_ID` as GitHub Actions secrets
   (repo → Settings → Secrets and variables → Actions). Pinterest starts
   posting automatically at the next scheduled run once these exist — no
   other change needed.

**Once #1 is done:**
3. Add `https://docs.designinfra.in/leads.html` to the Instagram bio link
   and Pinterest profile link so real visitors can actually reach the
   capture form.

**Still open, your call, no rush:**
4. RIO's expert-authority section (separate project, but worth noting
   here since it's now linked to Design Infra) needs your final public
   name/title and a short bio in your own words before it can go live.

## Where things live, if you want to look yourself

- `data/status.json` — the single source of truth for the dashboard's
  green/yellow/red status and headline numbers.
- `data/progress.json` — the day-by-day build log (this handover is Day 7,
  the last planned day).
- `DECISIONS.md` — every significant decision AURA has made, with the
  reasoning, newest first.
- `data/leads.json` / `data/lead_daily_report.json` — every lead ever
  logged and the daily rollup.
- `data/control.json` — kill switch state and the last test result.
- `scripts/heartbeat.py` — the actual logic for all of the above; readable
  Python, not a black box.

## What happens after Day 7

The build phase is done — all 7 planned days are complete. From here AURA
runs on her own schedule (heartbeat, daily publish, weekly content) and
responds to your issues. There's no "Day 8" unless you want to add a new
capability (a paid CRM once lead volume justifies it, expanding beyond
Instagram/Pinterest, etc.) — that would be a new decision for us to make
together when the time comes, not something pending right now.

If a future AURA session (a new Claude conversation) needs to pick this
up: read `README.md`, `DECISIONS.md`, `data/progress.json` and
`data/status.json` first, in that order, then this file.
