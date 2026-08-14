#!/usr/bin/env python3
"""AURA — Customer-Reaction QA (Kimi), the SECOND independent AI opinion.

Runs after creative_review.py (Gemini's expert-designer/marketer pass). This
one deliberately uses a different AI (Kimi/Moonshot) and a different persona —
not an expert, just an ordinary Delhi NCR homeowner scrolling Instagram — so a
post needs to clear two independently-minded checks, not one model's opinion,
before it reaches the owner's approval queue. Purely a second data point for
Vickey; never auto-publishes or auto-rejects.

Writes: data/customer_report.json  { "<date>": {...} }
Needs KIMI_API_KEY (see kimi_client.py). Fails open — skips with a note if the
key is missing or a call errors, never blocks the pipeline.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import kimi_client

ROOT = os.path.join(os.path.dirname(__file__), "..")

def jload(p, default):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except Exception:
        return default

def jsave(p, obj):
    json.dump(obj, open(os.path.join(ROOT, p), "w"), indent=1, ensure_ascii=False)

CUSTOMER_PROMPT = """You are an ordinary homeowner in Delhi NCR, India, mid-to-upper income, scrolling \
Instagram in the evening. You are NOT a marketer or designer — just a real potential customer who \
might one day hire an interior design company. You have just seen a post from "Design Infra", a \
turnkey interior design company. You did not see the image, only this text:

Hook (shown on the image): {hook}
Caption (below the post): {caption}
Hashtags: {hashtags}

Answer honestly and bluntly, as this person would actually think, not as a marketer would want you \
to answer. Reply with ONLY compact JSON, no markdown fences, in exactly this shape:
{{
  "would_stop_scrolling": true/false,
  "would_trust_the_brand": true/false,
  "confusing_words_or_terms": ["<any word/term an ordinary homeowner might not understand>", ...],
  "gut_reaction": "<one or two sentences, in your own words, exactly how you'd actually react>",
  "score": <integer 1-10, 10 = definitely would engage/save/message>
}}
Be specific about confusing_words_or_terms — flag any design jargon (e.g. an unexplained trend name) \
an average person wouldn't know without it being explained in the same post."""

def review_one(date, day):
    if not kimi_client.available():
        return {"skipped": True, "note": "KIMI_API_KEY not set — add it as a GitHub Secret to turn on the second AI opinion"}
    prompt = CUSTOMER_PROMPT.format(
        hook=day.get("ig", {}).get("hook_en", ""),
        caption=day.get("ig", {}).get("caption_hi", ""),
        hashtags=day.get("ig", {}).get("hashtags", ""),
    )
    try:
        return kimi_client.ask_json(prompt)
    except Exception as e:
        return {"error": True, "note": f"kimi review failed: {e}"}

if __name__ == "__main__":
    cal = jload("content/calendar.json", {"days": []})
    report = jload("data/customer_report.json", {})
    for day in cal.get("days", []):
        date = day["date"]
        v = review_one(date, day)
        report[date] = v
        print(f"{date}: {v.get('gut_reaction', v.get('note', ''))} (score={v.get('score', '-')})")
    jsave("data/customer_report.json", report)
    print(f"customer_review done: {len(report)} posts reviewed")
