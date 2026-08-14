#!/usr/bin/env python3
"""AURA — Creative Director QA (the "boss" over the image-vetting Gemini pass).

Runs after render_cards.mjs, once per week, on every freshly rendered post card.
Persona: a senior interior designer + a performance marketer for a premium
turnkey interior brand, reviewing one finished Instagram card at a micro level
before it ever reaches the owner's approval queue on the dashboard.

This does NOT auto-publish or auto-reject — the human approval gate
(data/approvals.json, see publisher.py) stays the final authority. This just
attaches an AI opinion + score so Vickey can approve/reject faster and with
more confidence, and so obviously-weak posts (generic hook, mismatched
terminology, awkward crop, illegible text) get caught before he ever sees them.

Writes: data/qa_report.json  { "<date>": {verdict, score, notes...} }
Needs GEMINI_API_KEY (same key as fetch_images.py). Fails open (skips with a
note) if the key is missing or a call errors — never blocks the pipeline.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gemini_client

ROOT = os.path.join(os.path.dirname(__file__), "..")

def jload(p, default):
    try:
        return json.load(open(os.path.join(ROOT, p)))
    except Exception:
        return default

def jsave(p, obj):
    json.dump(obj, open(os.path.join(ROOT, p), "w"), indent=1, ensure_ascii=False)

PERSONA_PROMPT = """You are the Creative Director for "Design Infra", a mid-to-premium turnkey \
interior design company in Delhi NCR, India, expanding pan-India. You wear two hats at once:

1. A senior INTERIOR DESIGNER (10+ years) who knows Indian residential design trends, materials, \
terminology, and can instantly spot a styling mistake, a mislabeled trend name, or a room that \
doesn't actually match what the caption claims.
2. A performance SOCIAL MEDIA MARKETER who has run hundreds of Instagram/Pinterest campaigns for \
home-services brands, and knows exactly what makes an Indian homeowner stop scrolling, save a post, \
or feel it's too generic/AI-generated/salesy to trust.

You are reviewing ONE finished Instagram post card image before it is shown to the business owner \
for final approval. Look at the image very carefully — actual room styling, photo quality, text \
placement/legibility/contrast, whether the text overlaps or clips awkwardly, whether it looks \
premium or cheap/stocky.

Here is the post's metadata (may not perfectly match what the image shows — check for mismatches):
Pillar/theme: {pillar}
Hook (English, on-image): {hook}
Caption (Hindi/Hinglish, in post body, not on image): {caption}
Hashtags: {hashtags}

Reply with ONLY compact JSON, no markdown fences, in exactly this shape:
{{
  "verdict": "pass" | "revise" | "reject",
  "score": <integer 1-10, 10 = ready to publish as-is>,
  "design_notes": "<one or two sentences from the interior-designer lens>",
  "marketing_notes": "<one or two sentences from the marketer lens: hook strength, scroll-stop power, trust>",
  "issues": ["<short specific issue>", ...],
  "fix_suggestion": "<one concrete, actionable fix if verdict is not pass, else empty string>"
}}
Be strict and specific — vague praise is not useful. A generic stock-looking room, a hook that could \
apply to any interior brand, or any text legibility problem should pull the score down and verdict \
to "revise". Only "reject" for something seriously wrong (wrong room type, offensive/irrelevant \
content, unreadable image)."""

def review_one(date, day):
    ig_path = os.path.join(ROOT, "content", "queue", f"{date}-ig.png")
    if not os.path.exists(ig_path):
        return {"verdict": "skipped", "score": 0, "note": "no rendered card found yet"}
    if not gemini_client.available():
        return {"verdict": "skipped", "score": 0, "note": "GEMINI_API_KEY not set — add it as a GitHub Secret to turn on AI review"}
    prompt = PERSONA_PROMPT.format(
        pillar=day.get("pillar", ""),
        hook=day.get("ig", {}).get("hook_en", ""),
        caption=day.get("ig", {}).get("caption_hi", ""),
        hashtags=day.get("ig", {}).get("hashtags", ""),
    )
    try:
        img = open(ig_path, "rb").read()
        verdict = gemini_client.ask_json(prompt, image_bytes=img, mime="image/png")
        verdict.setdefault("verdict", "revise")
        verdict.setdefault("score", 5)
        return verdict
    except Exception as e:
        return {"verdict": "error", "score": 0, "note": f"gemini review failed: {e}"}

if __name__ == "__main__":
    cal = jload("content/calendar.json", {"days": []})
    report = jload("data/qa_report.json", {})
    for day in cal.get("days", []):
        date = day["date"]
        v = review_one(date, day)
        report[date] = v
        print(f"{date}: verdict={v.get('verdict')} score={v.get('score')} — {v.get('marketing_notes', v.get('note', ''))}")
    jsave("data/qa_report.json", report)
    print(f"creative_review done: {len(report)} posts reviewed")
