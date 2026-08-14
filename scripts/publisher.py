#!/usr/bin/env python3
"""AURA — Publisher: posts today's queued content to Instagram + Pinterest.
Runs in GitHub Actions on cron. Skips gracefully when tokens are absent,
when the kill switch is ON, or when today's post is already published.

Secrets (GitHub Actions):
  IG_USER_ID       Instagram Business account ID
  IG_ACCESS_TOKEN  long-lived Instagram Graph API token
  PIN_ACCESS_TOKEN Pinterest API token
  PIN_BOARD_ID     Pinterest board to pin to
Repo state:
  data/control.json  {"kill_switch": false}
  content/published.json  log of published posts
  content/calendar.json   the schedule; images in content/queue/
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.join(os.path.dirname(__file__), "..")
IST = timezone(timedelta(hours=5, minutes=30))
today = datetime.now(IST).strftime("%Y-%m-%d")

def jload(p, default):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except Exception:
        return default

control = jload("data/control.json", {"kill_switch": False})
if control.get("kill_switch"):
    print("KILL SWITCH ON — publishing paused."); sys.exit(0)

published = jload("content/published.json", {})
cal = jload("content/calendar.json", {"days": []})
day = next((d for d in cal["days"] if d["date"] == today), None)
if not day:
    print("no scheduled post for", today); sys.exit(0)

REPO = os.environ.get("GITHUB_REPOSITORY", "vickykenin-lang/design-infra-marketing")
RAW = f"https://raw.githubusercontent.com/{REPO}/main"

def api(url, data=None, method=None):
    req = urllib.request.Request(url, method=method)
    body = urllib.parse.urlencode(data).encode() if data else None
    return json.load(urllib.request.urlopen(req, body, timeout=60))

def post_json(url, payload, headers):
    req = urllib.request.Request(url, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json", **headers})
    return json.load(urllib.request.urlopen(req, timeout=60))

log = published.setdefault(today, {})

# ---------- Instagram (feed photo via Graph API) ----------
IG_ID, IG_TOK = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
if IG_ID and IG_TOK and not log.get("instagram"):
    try:
        img_url = f"{RAW}/content/queue/{today}-ig.png"
        caption = f'{day["ig"]["hook_en"]}\n\n{day["ig"]["caption_hi"]}\n\n{day["ig"]["hashtags"]}'
        c = api(f"https://graph.facebook.com/v21.0/{IG_ID}/media",
                {"image_url": img_url, "caption": caption, "access_token": IG_TOK})
        r = api(f"https://graph.facebook.com/v21.0/{IG_ID}/media_publish",
                {"creation_id": c["id"], "access_token": IG_TOK})
        log["instagram"] = {"id": r.get("id"), "at": datetime.now(IST).isoformat()}
        print("instagram published:", r.get("id"))
    except Exception as e:
        print("instagram failed:", e, file=sys.stderr)
elif not (IG_ID and IG_TOK):
    print("instagram: tokens not set — skipping")

# ---------- Pinterest ----------
PIN_TOK, PIN_BOARD = os.environ.get("PIN_ACCESS_TOKEN"), os.environ.get("PIN_BOARD_ID")
if PIN_TOK and PIN_BOARD and not log.get("pinterest"):
    try:
        p = day["pinterest"]
        r = post_json("https://api.pinterest.com/v5/pins", {
            "board_id": PIN_BOARD, "title": p["title"][:100],
            "description": p["desc"][:500],
            "link": f"https://vickykenin-lang.github.io/design-infra-marketing/",
            "media_source": {"source_type": "image_url",
                             "url": f"{RAW}/content/queue/{today}-pin.png"}},
            {"Authorization": f"Bearer {PIN_TOK}"})
        log["pinterest"] = {"id": r.get("id"), "at": datetime.now(IST).isoformat()}
        print("pinterest published:", r.get("id"))
    except Exception as e:
        print("pinterest failed:", e, file=sys.stderr)
elif not (PIN_TOK and PIN_BOARD):
    print("pinterest: tokens not set — skipping")

json.dump(published, open(os.path.join(ROOT, "content/published.json"), "w"),
          indent=1, ensure_ascii=False)
