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

## 2026-08-17 — OPEN — New: third AI review voice added to the weekly pipeline

I've built and wired in a third independent review pass, alongside the
existing Gemini (`creative_review.py`) and Kimi (`customer_review.py`)
passes. This is infrastructure I built directly (not something you need to
do) — noting it here so you know it exists next time you read `data/`.

- New script: `scripts/business_review.py`, calling DeepSeek's API through
  `scripts/deepseek_client.py`. Persona: a homeowner actively comparing 2-3
  interior design companies before booking — a different lens from Gemini's
  expert-designer/marketer pass and Kimi's ordinary-scroller pass.
- Writes `data/business_report.json` — same shape/pattern as
  `data/qa_report.json` and `data/customer_report.json`.
- Wired into the `weekly` job in `.github/workflows/aura.yml`, right after
  the Kimi step. `continue-on-error: true`, same as the other two — never
  blocks the pipeline if the key is missing or a call fails.
- Same non-negotiable as the other two: this is a data point for the
  Founder's approval decision, not an auto-approve/auto-reject signal.

No action needed from you. It'll simply show up in `data/business_report.json`
starting with the next weekly run — mention it in your report if you notice
it (e.g. if `business_report.json` is empty/erroring, that's worth flagging).

## 2026-08-17 — OPEN — Small, single-purpose test command

Ignore everything else in this file for this one task. Do exactly this and
nothing more:

1. Fetch `https://raw.githubusercontent.com/vickykenin-lang/design-infra-marketing/main/data/status.json`
2. Reply in your next `aura_report_to_victor.md` entry with **only** this
   one line, filled in with the real value you actually received —
   no summary, no extra commentary, no other numbers:

   `VERIFICATION: updated field = <paste the exact literal value here>`

That's the whole task. If you cannot fetch that URL for any reason, write
`VERIFICATION: FAILED — <reason>` instead. Nothing else goes in this entry.

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

