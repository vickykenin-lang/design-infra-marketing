#!/usr/bin/env python3
"""AURA — Heartbeat: reads owner messages & kill switch (GitHub issues),
updates control state and dashboard data. Runs on cron + on issue events.
Uses GITHUB_TOKEN provided by Actions.
"""
import json, os, re, urllib.request
from datetime import datetime, timezone, timedelta
from lead_scoring import score_lead

ROOT = os.path.join(os.path.dirname(__file__), "..")
IST = timezone(timedelta(hours=5, minutes=30))
REPO = os.environ.get("GITHUB_REPOSITORY", "vickykenin-lang/design-infra-marketing")
TOK = os.environ.get("GITHUB_TOKEN", "")

def gh(path, data=None, method=None):
    req = urllib.request.Request(f"https://api.github.com/{path}", method=method,
        headers={"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"})
    body = json.dumps(data).encode() if data is not None else None
    with urllib.request.urlopen(req, body, timeout=30) as r:
        return json.load(r) if r.status != 204 else {}

def jload(p, default):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except Exception:
        return default

def jsave(p, obj):
    json.dump(obj, open(os.path.join(ROOT, p), "w"), indent=1, ensure_ascii=False)

control = jload("data/control.json", {"kill_switch": False})
inbox = jload("data/inbox.json", {"messages": []})
approvals = jload("data/approvals.json", {})
leads = jload("data/leads.json", {"leads": []})
OWNER = "vickykenin-lang"
now = datetime.now(IST).isoformat(timespec="minutes")

FIELD_RE = re.compile(r"^\s*[-*]?\s*(name|phone|city|project type|budget \(inr\)|budget|message)\s*:\s*(.*)$", re.IGNORECASE)


def parse_lead_body(body: str) -> dict:
    """Parses simple 'Key: value' lines (as produced by the dashboard's
    prefilled issue link and .github/ISSUE_TEMPLATE/new-lead.md) into a lead
    dict. Unrecognized/missing fields are left empty, never guessed."""
    fields = {"name": "", "phone": "", "city": "", "project_type": "", "budget_inr": None, "message": ""}
    for line in (body or "").splitlines():
        m = FIELD_RE.match(line)
        if not m:
            continue
        key, val = m.group(1).lower(), m.group(2).strip()
        if key == "name":
            fields["name"] = val
        elif key == "phone":
            fields["phone"] = val
        elif key == "city":
            fields["city"] = val
        elif key == "project type":
            fields["project_type"] = val
        elif key.startswith("budget"):
            digits = re.sub(r"[^\d]", "", val)
            fields["budget_inr"] = int(digits) if digits else None
        elif key == "message":
            fields["message"] = val
    return fields

issues = gh(f"repos/{REPO}/issues?state=open&per_page=50")
for i in issues:
    labels = [l["name"] for l in i.get("labels", [])]
    title = (i.get("title") or "").upper()
    body = i.get("body") or ""
    if "kill-switch" in labels or "KILL SWITCH" in title:
        control["kill_switch"] = True
        control["kill_reason"] = f"Issue #{i['number']} by {i['user']['login']} at {now}"
        gh(f"repos/{REPO}/issues/{i['number']}/comments",
           {"body": "🔴 Kill switch ACTIVATED — all publishing paused. / किल स्विच चालू — सारी पोस्टिंग रुकी। Resume: close this issue and comment RESUME, or ask AURA."})
        gh(f"repos/{REPO}/issues/{i['number']}", {"state": "closed"}, "PATCH")
        print("kill switch activated via issue", i["number"])
    elif (title.startswith("APPROVE 20") or title.startswith("REJECT 20")) and i["user"]["login"] == OWNER:
        action, date = title.split()[0], title.split()[1]
        approvals[date] = "approved" if action == "APPROVE" else "rejected"
        note = f"Reason: {body[:300]}" if (action == "REJECT" and body.strip()) else ""
        gh(f"repos/{REPO}/issues/{i['number']}/comments",
           {"body": ("✅ Approved — will publish at 19:00 IST. / मंज़ूर — शाम 7 बजे छपेगा।" if action == "APPROVE"
                     else "❌ Rejected — will NOT publish. AURA will rework it. / नामंज़ूर — नहीं छपेगा, AURA इसे सुधारेगी।") + ("\n" + note if note else "")})
        gh(f"repos/{REPO}/issues/{i['number']}", {"state": "closed"}, "PATCH")
        print(f"approval: {date} -> {approvals[date]}")
    elif "owner-message" in labels or "MESSAGE TO AURA" in title:
        inbox["messages"].append({"at": now, "from": i["user"]["login"],
                                  "issue": i["number"], "text": body[:2000]})
        gh(f"repos/{REPO}/issues/{i['number']}/comments",
           {"body": "✅ Message received — AURA will act on it in the next working session. / संदेश मिल गया — AURA अगले सेशन में इस पर काम करेगी।"})
        gh(f"repos/{REPO}/issues/{i['number']}", {"state": "closed"}, "PATCH")
        print("owner message stored from issue", i["number"])
    elif "new-lead" in labels or "NEW LEAD" in title:
        lead_fields = parse_lead_body(body)
        result = score_lead(lead_fields)
        lead_record = {
            "at": now, "issue": i["number"], "logged_by": i["user"]["login"],
            **lead_fields, "score": result["score"], "priority": result["priority"],
            "breakdown": result["breakdown"],
        }
        leads["leads"].append(lead_record)
        badge = {"HOT": "🔥 HOT", "WARM": "🌤️ WARM", "COLD": "❄️ COLD"}[result["priority"]]
        reasons_en = "\n".join(f"- {f['factor']}: {f['points']}/{f['max']} — {f['reason']}" for f in result["breakdown"])
        gh(f"repos/{REPO}/issues/{i['number']}/comments",
           {"body": f"📋 Lead logged — score {result['score']}/100, priority {badge}.\n\n{reasons_en}\n\n"
                    "यह लीड दर्ज हो गई है और डैशबोर्ड पर दिख रही है। / This lead is now on the dashboard."})
        gh(f"repos/{REPO}/issues/{i['number']}", {"state": "closed"}, "PATCH")
        print(f"lead logged from issue {i['number']}: score {result['score']} ({result['priority']})")

# resume check: closed kill issues with RESUME comment are handled manually by AURA sessions.

status = jload("data/status.json", {})
status["updated"] = now
status["kill_switch"] = control.get("kill_switch", False)
published = jload("content/published.json", {})
n_ig = sum(1 for d in published.values() if "instagram" in d)
n_pin = sum(1 for d in published.values() if "pinterest" in d)
n_posts = n_ig + n_pin
stats = status.setdefault("stats", {})
stats["posts"] = n_posts
cal = jload("content/calendar.json", {"days": []})
today = datetime.now(IST).strftime("%Y-%m-%d")
future_days = [d["date"] for d in cal.get("days", []) if d["date"] >= today]
# "scheduled" used to count every future calendar day regardless of approval
# status, which silently included days stuck on "rejected" (e.g. leftover
# test issues from a dress rehearsal) as if they were healthy and about to
# publish. Split it honestly instead: approved-and-will-publish vs
# pending-and-needs-your-review vs rejected-and-will-not-publish -- so the
# dashboard surfaces exactly what Vicky asked for: a visible review queue,
# not a number that hides whether anything is actually blocked
# (Dr. Victor, 2026-08-17, per Vicky: "approval should be in queue").
approved_days = [d for d in future_days if approvals.get(d) == "approved"]
rejected_days = [d for d in future_days if approvals.get(d) == "rejected"]
pending_days = [d for d in future_days if d not in approvals]
stats["scheduled"] = len(approved_days)
stats["pending_review"] = len(pending_days)
stats["rejected"] = len(rejected_days)

# Component statuses and the overall narrative were previously hardcoded from Day 1
# and never revisited, so the dashboard kept saying "no automation running yet" and
# "Publisher (Instagram): pending" even after real posts went out (caught in Dr.
# Victor's 2026-08-16 audit). Derive them from actual data on every heartbeat instead.
credits = jload("content/assets/credits.json", {})

# Day 5 (Dr. Victor, 2026-08-16): Lead Manager + Analyst are now real --
# leads.json/lead_scoring.py/leads.html exist and the heartbeat processes
# "NEW LEAD" issues above. Green means the pipeline is live, not that leads
# have arrived yet (zero real leads today is an honest, expected state for a
# brand-new public capture page, not a fault).
component_status = {
    "Dashboard": "green",
    "Content engine": "green" if credits else "pending",
    "Publisher (Instagram)": "green" if n_ig > 0 else "pending",
    "Publisher (Pinterest)": "green" if n_pin > 0 else "pending",
    "Lead Manager": "green",
    "Analyst": "green",
}
for c in status.get("components", []):
    if c.get("name") in component_status:
        c["status"] = component_status[c["name"]]

# --- Day 5: leads daily report ---
today_leads = [l for l in leads["leads"] if l["at"][:10] == today]
week_ago = (datetime.now(IST) - timedelta(days=7)).strftime("%Y-%m-%d")
week_leads = [l for l in leads["leads"] if l["at"][:10] >= week_ago]
hot_leads = sorted([l for l in leads["leads"] if l["priority"] == "HOT"], key=lambda l: -l["score"])
avg_score_week = round(sum(l["score"] for l in week_leads) / len(week_leads), 1) if week_leads else 0
stats["leads"] = len(leads["leads"])
daily_report = {
    "updated": now,
    "today": today,
    "leads_today": len(today_leads),
    "leads_this_week": len(week_leads),
    "leads_total": len(leads["leads"]),
    "avg_score_this_week": avg_score_week,
    "hot_leads_awaiting_followup": [
        {"issue": l["issue"], "name": l.get("name") or "(no name given)", "city": l.get("city", ""),
         "score": l["score"], "at": l["at"]}
        for l in hot_leads[:10]
    ],
    "note_en": (
        f"{len(today_leads)} lead(s) today, {len(week_leads)} this week, avg score {avg_score_week}/100."
        if leads["leads"] else
        "No leads yet — leads.html is live and ready to capture inquiries; none have come in yet."
    ),
    "note_hi": (
        f"आज {len(today_leads)} लीड, इस हफ़्ते {len(week_leads)}, औसत स्कोर {avg_score_week}/100।"
        if leads["leads"] else
        "अभी तक कोई लीड नहीं — leads.html लाइव और तैयार है, अभी तक कोई पूछताछ नहीं आई।"
    ),
}

if n_posts > 0:
    pending_note_en = f" {stats['pending_review']} awaiting your review." if stats["pending_review"] else ""
    pending_note_hi = f" {stats['pending_review']} आपकी समीक्षा का इंतज़ार कर रही हैं।" if stats["pending_review"] else ""
    status["overall_note_en"] = (
        f"Publishing live — {n_ig} Instagram post(s) out, {stats['scheduled']} approved and scheduled.{pending_note_en} "
        "Calendar auto-refills weekly so the queue never runs dry (Dr. Victor, 2026-08-17)."
    )
    status["overall_note_hi"] = (
        f"पब्लिशिंग लाइव — {n_ig} इंस्टाग्राम पोस्ट हो चुकी हैं, {stats['scheduled']} मंज़ूर और शेड्यूल हैं।{pending_note_hi} "
        "कैलेंडर हर हफ़्ते अपने-आप भर जाता है ताकि कतार कभी खाली न हो (Dr. Victor, 2026-08-17)।"
    )
else:
    status["overall_note_en"] = "Day 1 build in progress. No automation running yet."
    status["overall_note_hi"] = "दिन 1 का निर्माण जारी। अभी कोई ऑटोमेशन नहीं चल रहा।"

jsave("data/status.json", status)
jsave("data/control.json", control)
jsave("data/inbox.json", inbox)
jsave("data/approvals.json", approvals)
jsave("data/leads.json", leads)
jsave("data/lead_daily_report.json", daily_report)
print("heartbeat done:", json.dumps(stats))
