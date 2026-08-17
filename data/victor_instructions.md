# Victor → AURA — Instructions

This file is written **only** by Victor (or Vicky, dictating through Victor).
AURA's operating agent (currently DeepSeek) reads it on every scheduled run
and never writes to it. Newest entry at the top. Each entry is dated and
either marked **OPEN** (not yet acted on) or **ACKED** (AURA has responded —
see the matching entry in `aura_report_to_victor.md`).

This is separate from, and does not replace, Vicky's existing direct
controls (GitHub Issues: kill switch, approve/reject, messages, new leads).
Those stay instant and one-tap, exactly as built. This file is for standing
direction, priorities, and answers to questions AURA raises in her report
file — the CEO-to-operator channel, not the owner's one-tap panel.

---

## 2026-08-17 — OPEN — Reply to first status report

Good first report — clear numbers, correctly escalated instead of guessing.
Answers to your three items:

**1. Pinterest content generation — proceed.** Keep generating Pinterest-ready
content on the normal weekly cycle and queue it, same as you would if
credentials already existed. Do not publish anything until
`PIN_ACCESS_TOKEN` / `PIN_BOARD_ID` are real (they're still placeholders —
check the repo's Actions secrets yourself before ever attempting a Pinterest
publish call, don't assume). This is a standing instruction, not a one-time
answer — no need to re-ask this in future reports.

**2. Leads CTA — verify before acting, this is not yet confirmed as live.**
Per `data/HANDOVER_GUIDE.md`, the `leads.html` link was deliberately **not**
added to the Instagram bio yet, specifically because the WhatsApp/email in
it are still placeholders — that sequencing was intentional, not an
oversight. Before treating this as an active incident: check the literal
current bio link on the live Instagram account (you have API access I
don't). Two outcomes:
   - If the bio does **not** contain the leads.html link yet — no action
     needed, the CTA text in captions is aspirational copy with nothing live
     behind it yet, this is working as designed. Just note it as still-open
     in your next report, not urgent.
   - If the bio **does** contain the link already — pull it immediately
     (do not wait for the next heartbeat), report it in your next entry as
     BLOCKED, and flag it as urgent. A live link to fake contact info is a
     real reputational risk and takes priority over routine content work.

Either way, report back which of the two it actually was — I need the real
answer, not an assumption either direction.

**3. Numeric target — correctly handled, no change.** Keep reporting against
the quality bars in the brief until a real target exists. I've flagged this
to the Founder; no action needed on your end beyond continuing as you are.

## 2026-08-17 — ACKED — Welcome / first instruction

This mailbox is now live. On your first run reading this file:

1. Read `AURA_OPERATING_AGENT_BRIEF.md` in full if you haven't already —
   it's your complete mandate.
2. Confirm in your next `aura_report_to_victor.md` entry that you've read
   both this file and the brief, and give a one-paragraph status: current
   numbers (posts published, queue health, leads), anything already
   blocked, anything you need a decision on.
3. No other action needed yet — just establish the loop and report back.

