"""AURA — shared Gemini REST client (no SDK needed, just urllib).
Used by fetch_images.py (photo authenticity check) and creative_review.py
(final post QA, the "creative director" pass before owner approval).

Needs GEMINI_API_KEY as an env var / GitHub Secret. If it's missing or a
call fails, callers must fail OPEN (don't block the pipeline) but log loudly
so a human notices in fetch_log.txt / qa_report.json.

Google keeps retiring model names (we've hit two dead models already:
gemini-2.0-flash, then gemini-2.5-flash "no longer available to new users").
To stop chasing this by hand every few months, we try a short list of
current model names in order and remember whichever one actually worked for
the rest of this process — so ONE stale name in the list no longer breaks
the whole pipeline.
"""
import base64, json, os, urllib.error, urllib.request

_env_model = os.environ.get("GEMINI_MODEL", "").strip()
MODEL_CANDIDATES = [m for m in [
    _env_model or None,
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash",
] if m]
API_KEY = os.environ.get("GEMINI_API_KEY", "")
_working_model = None  # cached once we find a model name that actually responds


def available():
    return bool(API_KEY)


def _endpoint(model):
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def ask(prompt, image_bytes=None, mime="image/jpeg", timeout=60):
    """Send a text (+ optional image) prompt to Gemini, return the raw text reply.
    Raises on any failure — callers decide how to fail open."""
    global _working_model
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    parts = [{"text": prompt}]
    if image_bytes is not None:
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode()}})
    body = json.dumps({
        "contents": [{"parts": parts}],
        # 700 was too small for a full JSON verdict (design_notes + marketing_notes +
        # issues[] + fix_suggestion) — replies were getting cut off mid-string, which
        # then failed JSON parsing downstream ("Unterminated string ..."). Also bumped
        # the per-call timeout since gemini-3.x vision calls run a bit slower than the
        # old 2.0-flash did.
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }).encode()

    models_to_try = [_working_model] if _working_model else MODEL_CANDIDATES
    last_err = None
    for model in models_to_try:
        req = urllib.request.Request(
            f"{_endpoint(model)}?key={API_KEY}", data=body, method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.load(r)
            _working_model = model  # remember it, skip the retry list next call
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            # urllib's default str(e) is just "HTTP Error 404: Not Found" — the actual
            # reason (bad key, wrong/retired model, API not enabled, etc.) is in the body.
            try:
                detail = e.read().decode(errors="replace")[:300]
            except Exception:
                detail = "(could not read error body)"
            last_err = RuntimeError(f"HTTP {e.code} from Gemini (model={model}): {detail}")
            if e.code == 404:
                continue  # this model name is dead/unavailable — try the next candidate
            raise last_err
    raise last_err


def ask_json(prompt, image_bytes=None, mime="image/jpeg", timeout=60):
    """Same as ask(), but strips markdown fences and parses JSON. Raises on failure."""
    txt = ask(prompt, image_bytes, mime, timeout).strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:]
    txt = txt.strip()
    try:
        # strict=False lets literal newlines/control characters inside string values
        # through — Gemini sometimes writes a real newline instead of an escaped \n
        # even when asked for compact JSON, which a strict parser rejects outright.
        return json.loads(txt, strict=False)
    except json.JSONDecodeError:
        # Fall back to the substring between the first { and the last } — handles
        # cases where the model added stray text before/after the JSON object.
        start, end = txt.find("{"), txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(txt[start:end + 1], strict=False)
        raise
