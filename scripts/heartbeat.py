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
n_posts = sum(1 for d in published.values() for k in d if k in ("instagram", "pinterest"))
stats = status.setdefault("stats", {})
stats["posts"] = n_posts
cal = jload("content/calendar.json", {"days": []})
today = datetime.now(IST).strftime("%Y-%m-%d")
stats["scheduled"] = sum(1 for d in cal.get("days", []) if d["date"] >= today)
jsave("data/status.json", status)
jsave("data/control.json", control)
jsave("data/inbox.json", inbox)
print("heartbeat done:", json.dumps(stats))
