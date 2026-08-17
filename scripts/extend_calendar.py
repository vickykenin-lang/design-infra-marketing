#!/usr/bin/env python3
"""AURA — Calendar Extender: keeps content/calendar.json topped up so the
publishing pipeline never runs dry.

Root cause this fixes (Dr. Victor, 2026-08-17, per Vicky's "image generation
shouldn't stop, approval should be in queue" question): calendar.json was
hand-authored once for a single pilot week (2026-08-15 .. 2026-08-21) and
nothing ever extended it. Once that last date passes, publisher.py finds no
matching day and exits quietly, and the dashboard's approval queue shows
"No upcoming posts" -- from the owner's side this looks exactly like
"automation stopped", even though nothing actually broke.

What this script does, every time it runs (wired into the weekly job,
before fetch_images.py/render_cards.mjs so a newly-added week gets real
images before it's due):
  1. Look at the last date already in calendar.json.
  2. If the buffer (days between "today" and that last date) has dropped
     below BUFFER_DAYS, generate NEW_DAYS more days, continuing the same
     content-pillar rotation and cadence documented in brand/BRAND.md.
  3. Each new day is written with NO entry in approvals.json -- that is the
     existing "pending" state (see heartbeat.py / index.html's approvals
     panel), so new content always enters an owner-reviewable queue. This
     script never sets a day to "approved" -- only the owner (via the
     dashboard's Approve/Reject buttons, i.e. real GitHub issues) can do
     that. That is the actual fix for "approval should be in queue": there
     is always something queued, and it is never auto-approved.

Fails OPEN, loudly: if Gemini is unavailable or errors, falls back to a
simple on-brand template so the pipeline still gets new (lower-effort) days
queued rather than silently stalling -- and prints clearly which path was
used so it shows up in the Actions log.
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import gemini_client

ROOT = os.path.join(os.path.dirname(__file__), "..")
IST = timezone(timedelta(hours=5, minutes=30))
CAL_PATH = os.path.join(ROOT, "content", "calendar.json")
APPROVALS_PATH = os.path.join(ROOT, "data", "approvals.json")

BUFFER_DAYS = 7   # keep at least this many future days queued at all times
NEW_DAYS = 7      # top up in one-week batches, matching the existing cadence

# Content pillars + weekly mix from brand/BRAND.md ("Content pillars (weekly
# mix)") -- a 20-slot weighted rotation approximates 30/25/20/15/10% without
# relying on randomness, so the sequence is reproducible run to run.
PILLAR_ROTATION = (
    ["Design Tips & Mistakes"] * 6 +
    ["Before/After & Concept Transformations"] * 5 +
    ["Budget & Process Transparency"] * 4 +
    ["Trends & Festive/Seasonal"] * 3 +
    ["Turnkey Education & Brand Story"] * 2
)
ROOMS = ["kitchen", "living", "bedroom", "bathroom", "office"]

PROMPT_TEMPLATE = """You are AURA, the AI Sales & Marketing CEO for Design Infra, a turnkey
interior design company in Delhi NCR, India (expanding to other metros).

Brand voice:
- Instagram: Hinglish -- an English hook line, then warm Hindi caption. Short sentences, one idea per post.
- Pinterest: clean, search-optimized English (Pinterest is a search engine, not a social feed).
- Always: honest "Concept visualisation" labels on any AI-concept image, no fake urgency, no "DM now!!!" spam tone.
- Positioning line: "Ek team, zero jhanjhat" -- one team, one contract, complete home, no juggling ten contractors.

Write ONE day's post for content pillar: "{pillar}"
Date: {date} ({weekday})
Room focus for the accompanying photo: {room}

Return ONLY compact JSON, no markdown fences, matching exactly this shape:
{{"format": "<short format label, e.g. 'tips card' or 'before/after' or 'quote card'>",
 "hook_en": "<one short punchy English hook line>",
 "caption_hi": "<2-3 warm Hindi sentences in Devanagari script, ending with a soft CTA about a free consultation>",
 "hashtags": "<5 relevant hashtags space-separated, each starting with #>",
 "pin_title": "<pinterest title, max 100 chars, search-optimized English>",
 "pin_desc": "<pinterest description, max 300 chars, search-optimized English>"}}
"""

# Simple, honest fallback if Gemini is unavailable -- lower production value
# than a real Gemini post, but keeps the queue alive rather than empty.
FALLBACK_BY_PILLAR = {
    "Design Tips & Mistakes": {
        "format": "tips card", "hook_en": "A mistake we see in almost every first meeting.",
        "caption_hi": "घर बनवाने से पहले यह एक बात ज़रूर जान लें। सही प्लानिंग से लाखों बच सकते हैं। मुफ़्त सलाह के लिए बायो में लिंक देखें।",
        "hashtags": "#InteriorDesignIndia #HomeRenovation #DesignTips #TurnkeyInteriors #DelhiNCR",
    },
    "Before/After & Concept Transformations": {
        "format": "concept transformation (labeled)", "hook_en": "Same room. Different life.",
        "caption_hi": "(Concept visualisation) सोच-समझकर डिज़ाइन किया गया एक कमरा कैसा दिखता है। आपका कमरा कौन-सा बन सकता है?",
        "hashtags": "#BeforeAfter #HomeMakeover #ConceptDesign #InteriorDesignDelhi #DreamHome",
    },
    "Budget & Process Transparency": {
        "format": "process card", "hook_en": "What actually goes into your quote.",
        "caption_hi": "पारदर्शिता हमारा वादा है — हर स्टेज पर आपकी मंज़ूरी, कोई छुपी हुई लागत नहीं। मुफ़्त सलाह के लिए बायो में लिंक देखें।",
        "hashtags": "#InteriorBudget #TransparentPricing #TurnkeyInteriors #HomeInteriors #DelhiNCR",
    },
    "Trends & Festive/Seasonal": {
        "format": "quote card", "hook_en": "A home that's ready for the season.",
        "caption_hi": "त्योहारों के मौसम में अपने घर को नया रूप दें — एक टीम, एक कॉन्ट्रैक्ट, ज़ीरो झंझट।",
        "hashtags": "#HomeInteriors #FestiveHome #InteriorDesignIndia #TurnkeyInteriors #DelhiNCR",
    },
    "Turnkey Education & Brand Story": {
        "format": "education card", "hook_en": "Why one team beats ten contractors.",
        "caption_hi": "डिज़ाइन से हैंडओवर तक, एक ही टीम — कोई राउंड-राउंड नहीं। यही है असली टर्नकी इंटीरियर।",
        "hashtags": "#TurnkeyInteriors #OneTeam #InteriorDesignIndia #HomeInteriors #DelhiNCR",
    },
}


def jload(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


def jsave(path, obj):
    json.dump(obj, open(path, "w"), indent=1, ensure_ascii=False)


def gen_day(date_str, pillar, room):
    """Try Gemini first; fall back to a template on any failure. Never raises."""
    weekday = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
    if gemini_client.available():
        try:
            data = gemini_client.ask_json(PROMPT_TEMPLATE.format(
                pillar=pillar, date=date_str, weekday=weekday, room=room))
            return {
                "date": date_str, "pillar": pillar, "photo_tag": room,
                "ig": {"format": data.get("format", "tips card"),
                       "hook_en": data["hook_en"], "caption_hi": data["caption_hi"],
                       "hashtags": data["hashtags"]},
                "pinterest": {"title": data.get("pin_title", data["hook_en"])[:100],
                              "desc": data.get("pin_desc", data["caption_hi"])[:300]},
                "source": "gemini",
            }
        except Exception as e:
            print(f"  Gemini generation failed for {date_str} ({pillar}): {e} -- using fallback template", file=sys.stderr)
    else:
        print(f"  GEMINI_API_KEY not set -- using fallback template for {date_str}", file=sys.stderr)
    fb = FALLBACK_BY_PILLAR[pillar]
    return {
        "date": date_str, "pillar": pillar, "photo_tag": room,
        "ig": {"format": fb["format"], "hook_en": fb["hook_en"],
               "caption_hi": fb["caption_hi"], "hashtags": fb["hashtags"]},
        "pinterest": {"title": fb["hook_en"], "desc": fb["caption_hi"]},
        "source": "fallback_template",
    }


def main():
    cal = jload(CAL_PATH, {"week_of": None, "days": []})
    approvals = jload(APPROVALS_PATH, {})
    today = datetime.now(IST).date()

    days = cal.get("days", [])
    last_date = max((datetime.strptime(d["date"], "%Y-%m-%d").date() for d in days), default=today - timedelta(days=1))
    buffer_days = (last_date - today).days

    print(f"today={today} last_queued={last_date} buffer={buffer_days} days (threshold={BUFFER_DAYS})")
    if buffer_days >= BUFFER_DAYS:
        print("buffer healthy -- nothing to do")
        return

    # Continue the pillar rotation from where the existing queue left off,
    # not from zero each time, so the weekly-mix percentages hold over time.
    start_idx = len(days) % len(PILLAR_ROTATION)
    new_days = []
    for i in range(NEW_DAYS):
        d = last_date + timedelta(days=i + 1)
        pillar = PILLAR_ROTATION[(start_idx + i) % len(PILLAR_ROTATION)]
        room = ROOMS[(start_idx + i) % len(ROOMS)]
        entry = gen_day(d.isoformat(), pillar, room)
        new_days.append(entry)
        # Deliberately NOT touching approvals.json here -- an absent entry
        # is the existing "pending, awaiting your decision" state the
        # dashboard already renders with Approve/Reject buttons. New
        # content is queued for review, never auto-approved.
        print(f"  queued {d.isoformat()} [{pillar}] via {entry['source']}")

    days.extend(new_days)
    cal["days"] = days
    cal["week_of"] = days[0]["date"] if days else cal.get("week_of")
    jsave(CAL_PATH, cal)
    print(f"calendar.json: +{len(new_days)} days, {len(days)} total, now buffered through {days[-1]['date']}")


if __name__ == "__main__":
    main()
