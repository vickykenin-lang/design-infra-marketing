#!/usr/bin/env python3
"""AURA — Heartbeat: reads owner messages & kill switch (GitHub issues),
updates control state and dashboard data. Runs on cron + on issue events.
Uses GITHUB_TOKEN provided by Actions.
"""
import json, os, urllib.request
from datetime import datetime, timezone, timedelta

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
OWNER = "vickykenin-lang"
now = datetime.now(IST).isoformat(timespec="minutes")

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
stats["scheduled"] = sum(1 for d in cal.get("days", []) if d["date"] >= today)

# Component statuses and the overall narrative were previously hardcoded from Day 1
# and never revisited, so the dashboard kept saying "no automation running yet" and
# "Publisher (Instagram): pending" even after real posts went out (caught in Dr.
# Victor's 2026-08-16 audit). Derive them from actual data on every heartbeat instead.
credits = jload("content/assets/credits.json", {})
component_status = {
    "Dashboard": "green",
    "Content engine": "green" if credits else "pending",
    "Publisher (Instagram)": "green" if n_ig > 0 else "pending",
    "Publisher (Pinterest)": "green" if n_pin > 0 else "pending",
    "Lead Manager": "pending",   # Day 5 build not started yet
    "Analyst": "pending",        # Day 5 build not started yet
}
for c in status.get("components", []):
    if c.get("name") in component_status:
        c["status"] = component_status[c["name"]]

if n_posts > 0:
    status["overall_note_en"] = (
        f"Publishing live — {n_ig} Instagram post(s) out, {stats['scheduled']} more scheduled this week. "
        "Image-relevance filter bug fixed 2026-08-16 (Dr. Victor audit)."
    )
    status["overall_note_hi"] = (
        f"पब्लिशिंग लाइव — {n_ig} इंस्टाग्राम पोस्ट हो चुकी हैं, इस हफ़्ते {stats['scheduled']} और शेड्यूल हैं। "
        "इमेज-रिलेवेंस फ़िल्टर की गड़बड़ी 2026-08-16 को ठीक कर दी गई (Dr. Victor ऑडिट)।"
    )
else:
    status["overall_note_en"] = "Day 1 build in progress. No automation running yet."
    status["overall_note_hi"] = "दिन 1 का निर्माण जारी। अभी कोई ऑटोमेशन नहीं चल रहा।"

jsave("data/status.json", status)
jsave("data/control.json", control)
jsave("data/inbox.json", inbox)
jsave("data/approvals.json", approvals)
print("heartbeat done:", json.dumps(stats))
