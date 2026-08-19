# AURA Correction A — Metric Honesty Patch
**Prepared by Dr. Victor · 19 Aug 2026**

## Problem
`scripts/heartbeat.py` currently sets overall status narrative based on posts published.
It can report “green / Publishing live” while real qualified leads = 0.
This is the exact false-green pattern flagged in the 18 Aug audit.

## Required change in `scripts/heartbeat.py`

After the leads daily report is built and `stats["leads"]` is set, add logic that:

1. Counts **real** leads (exclude any lead whose name or message clearly marks it as a test/rehearsal).
2. Forces overall status and notes as follows:

```python
# --- Metric honesty (Dr. Victor, 2026-08-19) ---
# Real leads only — exclude dress-rehearsal / test leads
real_leads = [
    l for l in leads["leads"]
    if "test" not in (l.get("name") or "").lower()
    and "rehearsal" not in (l.get("message") or "").lower()
    and "test lead" not in (l.get("message") or "").lower()
]
real_lead_count = len(real_leads)
stats["real_leads"] = real_lead_count

if real_lead_count == 0:
    status["overall"] = "red"
    status["overall_note_en"] = (
        f"BUSINESS RED — 0 real qualified leads. "
        f"Process is running ({n_ig} IG posts published, {stats['pending_review']} awaiting review) "
        f"but the only metric that matters is still zero. "
        f"Founder inputs still required: real WhatsApp/email in leads.html, project photos, GBP status."
    )
    status["overall_note_hi"] = (
        f"बिज़नेस रेड — 0 असली क्वालीफाइड लीड। "
        f"प्रोसेस चल रहा है ({n_ig} IG पोस्ट, {stats['pending_review']} समीक्षा में) "
        f"लेकिन असली मेट्रिक अभी भी शून्य है।"
    )
elif real_lead_count < 3:
    status["overall"] = "yellow"
    status["overall_note_en"] = (
        f"Early traction — {real_lead_count} real qualified lead(s). "
        f"Keep publishing quality content and close the remaining founder inputs."
    )
    status["overall_note_hi"] = (
        f"शुरुआती ट्रैक्शन — {real_lead_count} असली क्वालीफाइड लीड। "
        f"क्वालिटी कंटेंट जारी रखें।"
    )
else:
    status["overall"] = "green"
    # keep or refine the existing positive note
```

Place this block **after** `stats["leads"] = len(leads["leads"])` and **before** the final `jsave("data/status.json", status)`.

## Why this is durable
`status.json` is overwritten by every heartbeat. Only changing the generator (`heartbeat.py`) makes the honesty permanent.
