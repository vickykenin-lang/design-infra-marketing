# DECISIONS.md — AURA's Decision Log

Every significant decision, one line of reasoning each. Newest on top.

| Date | Decision | Reasoning |
|------|----------|-----------|
| 2026-08-19 | **Dashboard display rule LOCKED:** never show rejected cards/images. Show only **approved** posts OR cards with **business score ≥ 7**. Implemented in `index.html` (`isDashboardEligible`). | Founder directive: rejected images must not appear on the dashboard; only quality-eligible content. |
| 2026-08-19 | Rigid zero-cost-only rule for content assets is **archived**. New rule: prefer free/already-available tools first; controlled low-cost tools allowed when free options fail quality; any new account/credit-card/paid API still requires Founder approval. Real project photos remain highest priority. Image Generation Playbook written (`data/IMAGE_GENERATION_PLAYBOOK.md`). | Free Wikimedia/Openverse pool is producing 1–4/10 mismatched, archival, non-Indian images and actively blocking conversion. Continuing the old rule while real leads = 0 is no longer rational. Gemini (already in stack) becomes primary AI image source with mandatory “Concept visualisation” label. |
| 2026-08-19 | Metric honesty patch applied to `scripts/heartbeat.py`: overall status forced red when real qualified leads = 0 (test/rehearsal leads excluded). Pending review queue and Content Guidelines V2 published. | Process-green while business-red was the exact false-green pattern flagged in the 18 Aug audit. Single success metric is qualified leads. |
| 2026-08-17 | Day 7 (final build day) complete: live dress rehearsal ran two real GitHub-issue tests (kill switch #30, new-lead intake #31), both confirmed end-to-end on the live dashboard; wrote `data/HANDOVER_GUIDE.md` consolidating what AURA does automatically, the one-tap dashboard controls, and the 3 remaining owner-only setup items | Closes out the planned 7-day build. |
| 2026-08-17 | Day 6 kill-switch test run live (issue #30, with Vicky watching) | Confirms the single most safety-critical control works end-to-end. |
| 2026-08-16 | Day 5 (Leads + Analytics) built | Lead pipeline live. |
| 2026-08-16 | KPI targets set for the current build phase | Measure one real month first. |
| 2026-08-16 | Lead-handoff point: GitHub Issues + leads.html | Zero-cost interim. |
| 2026-08-14 | Positioning language Hindi for owner; content bilingual | Owner chose Hindi. |
| 2026-08-14 | Differentiators: true turnkey, pan-India metros, milestone transparency, design-first | Founder delegated. |
| 2026-08-14 | Company profile captured: Design Infra, Delhi NCR, turnkey, mid-to-premium | Day 1. |
