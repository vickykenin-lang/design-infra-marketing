"""AURA — shared Gemini REST client (no SDK needed, just urllib).
Used by fetch_images.py (photo authenticity check) and creative_review.py
(final post QA, the "creative director" pass before owner approval).

Needs GEMINI_API_KEY as an env var / GitHub Secret. If it's missing or a
call fails, callers must fail OPEN (don't block the pipeline) but log loudly
so a human notices in fetch_log.txt / qa_report.json.
"""
import base64, json, os, urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"


def available():
    return bool(API_KEY)


def ask(prompt, image_bytes=None, mime="image/jpeg", timeout=45):
    """Send a text (+ optional image) prompt to Gemini, return the raw text reply.
    Raises on any failure — callers decide how to fail open."""
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    parts = [{"text": prompt}]
    if image_bytes is not None:
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}})
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 700},
    }).encode()
    req = urllib.request.Request(
        f"{ENDPOINT}?key={API_KEY}", data=body, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def ask_json(prompt, image_bytes=None, mime="image/jpeg", timeout=45):
    """Same as ask(), but strips markdown fences and parses JSON. Raises on failure."""
    txt = ask(prompt, image_bytes, mime, timeout).strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:]
    return json.loads(txt.strip())
