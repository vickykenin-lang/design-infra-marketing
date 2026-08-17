#!/usr/bin/env python3
"""AURA — Comparison-Shopper QA (DeepSeek), the THIRD independent AI opinion.

Runs after creative_review.py (Gemini's expert-designer/marketer pass) and
customer_review.py (Kimi's ordinary-homeowner gut-reaction pass). This one
uses a third, independently-built AI (DeepSeek) with yet another persona —
not an expert, not a casual scroller, but a homeowner ALREADY ACTIVELY
COMPARING Design Infra against 2-3 other interior design companies before
spending lakhs of rupees. Three independently-minded checks from three
different labs catch more than any one model's blind spot. Purely a third
data point for Vickey; never auto-publishes or auto-rejects.

Writes: data/business_report.json  { "<date>": {...} }
Needs DEEPSEEK_API_KEY (see deepseek_client.py). Fails open — skips with a
note if the key is missing or a call errors, never blocks the pipeline.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import deepseek_client

ROOT = os.path.join(os.path.dirname(__file__), "..")

def jload(p, default):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except Exception:
        return default

def jsave(p, obj):
    json.dump(obj, open(os.path.join(ROOT, p), "w"), indent=1, ensure_ascii=False)

COMPARISON_PROMPT = """You are a homeowner in Delhi NCR, India, mid-to-upper income, currently \
ACTIVELY comparing 2-3 turnkey interior design companies before committing lakhs of rupees to one \
of them. You have shortlisted a few Instagram accounts, including "Design Infra", and are scrolling \
through their recent posts specifically to decide who to book a consultation with. You did not see \
the image, only this text:

Hook (shown on the image): {hook}
Caption (below the post): {caption}
Hashtags: {hashtags}

Think like someone comparing vendors, not just browsing for fun — you're weighing trust, \
transparency, and whether this company feels more credible than the others you're considering. \
Reply with ONLY compact JSON, no markdown fences, in exactly this shape:
{{
  "would_shortlist_over_competitors": true/false,
  "builds_trust_vs_generic_ad": true/false,
  "missing_info_a_comparison_shopper_would_want": ["<e.g. pricing hint, timeline, warranty>", ...],
  "gut_reaction": "<one or two sentences, in your own words, exactly how you'd actually react>",
  "score": <integer 1-10, 10 = this alone would make you book a consultation>
}}
Be specific about missing_info_a_comparison_shopper_would_want — flag anything a genuine \
vendor-comparison shopper would want to see before reaching out (cost transparency signals, \
timeline honesty, proof of real projects) that this post doesn't address."""

def review_one(date, day):
    if not deepseek_client.available():
        return {"skipped": True, "note": "DEEPSEEK_API_KEY not set — add it as a GitHub Secret to turn on the third AI opinion"}
    prompt = COMPARISON_PROMPT.format(
        hook=day.get("ig", {}).get("hook_en", ""),
        caption=day.get("ig", {}).get("caption_hi", ""),
        hashtags=day.get("ig", {}).get("hashtags", ""),
    )
    try:
        return deepseek_client.ask_json(prompt)
    except Exception as e:
        return {"error": True, "note": f"deepseek review failed: {e}"}

if __name__ == "__main__":
    cal = jload("content/calendar.json", {"days": []})
    report = jload("data/business_report.json", {})
    for day in cal.get("days", []):
        date = day["date"]
        v = review_one(date, day)
        report[date] = v
        print(f"{date}: {v.get('gut_reaction', v.get('note', ''))} (score={v.get('score', '-')})")
    jsave("data/business_report.json", report)
    print(f"business_review done: {len(report)} posts reviewed")
