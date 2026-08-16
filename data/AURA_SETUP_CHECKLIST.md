# AURA Setup Checklist for Vicky

Drafted 2026-08-16 by Dr. Victor, alongside the Day 5 (Leads + Analytics)
build. Each item is a one-time, few-minutes task. AURA/RIO cannot do any of
these (account creation and real contact-detail decisions are founder-only).

## 1. Add real contact details to the lead-capture page (before sharing it publicly)

- Open `leads.html`, find the `CONFIG` block near the top of the `<script>`.
- Replace `BUSINESS_WHATSAPP` (currently a placeholder `"91XXXXXXXXXX"`)
  with Design Infra's real WhatsApp Business number, digits only, country
  code first, no `+` or spaces (e.g. `919812345678`).
- Replace `BUSINESS_EMAIL` (currently a placeholder
  `"leads@designinfra.in"`) with the real inbox you want inquiries sent to.
- Until this is updated, the form still works but will try to hand leads
  off to placeholder contacts — don't share the `leads.html` link publicly
  (e.g. in Instagram/Pinterest bio) until this is done.

## 2. Pinterest connection (still pending from Day 4)

- Add `PIN_ACCESS_TOKEN` and `PIN_BOARD_ID` as GitHub Actions secrets on
  the repo (Settings → Secrets and variables → Actions).
- Once added, Pinterest auto-posting starts at the next scheduled publish
  run — no other change needed.

## 3. Share the lead-capture link

- Once item 1 is done, add `https://docs.designinfra.in/leads.html` (or
  wherever the site is hosted) to the Instagram bio link and Pinterest
  profile link, so real visitors can actually reach it.

## How to log a lead that comes in by phone/WhatsApp/in person

- Open the dashboard (`index.html`) → Leads card → "Log a new lead" button.
  This opens a pre-filled GitHub issue form — fill in whatever you know,
  submit, and AURA scores and logs it within a few hours (next heartbeat).
- Or open a new GitHub issue directly using the "New lead" issue template.

## Status as of 2026-08-16

Leads pipeline (capture page, scoring, GitHub-Issues intake, dashboard
report) is built and live. Zero real leads exist yet — that's expected for
a brand-new form, not a fault. Items 1-3 above are what's blocking real
inquiries from reaching you.
