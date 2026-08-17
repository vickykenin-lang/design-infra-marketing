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
import base64, json, os, time, urllib.error, urllib.request

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

    # Try the cached working model first (fast path), but if IT starts failing
    # (e.g. temporarily overloaded), fall back to the full candidate list instead
    # of giving up — don't let one model's bad day take down the whole run.
    if _working_model:
        models_to_try = [_working_model] + [m for m in MODEL_CANDIDATES if m != _working_model]
    else:
        models_to_try = MODEL_CANDIDATES
    last_err = None
    for model in models_to_try:
        req = urllib.request.Request(
            f"{_endpoint(model)}?key={API_KEY}", data=body, method="POST",
            headers={"Content-Type": "application/json"})
        # 429 (rate limited) / 503 ("high demand, try again later") are transient —
        # a couple of short retries clears most of them without burning a whole
        # candidate-model slot on what is really just a temporary Google-side hiccup.
        status_code = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    data = json.load(r)
                _working_model = model  # remember it, skip the retry list next call
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                status_code = e.code
                # urllib's default str(e) is just "HTTP Error 404: Not Found" — the
                # actual reason (bad key, retired model, overloaded, ...) is in the body.
                try:
                    detail = e.read().decode(errors="replace")[:300]
                except Exception:
                    detail = "(could not read error body)"
                last_err = RuntimeError(f"HTTP {e.code} from Gemini (model={model}): {detail}")
                if status_code in (429, 503) and attempt < 2:
                    time.sleep(3 * (attempt + 1))  # 3s, then 6s, then give up on this model
                    continue
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                # Network-level failure (read timeout, connection reset, DNS hiccup) —
                # there is no HTTP status here at all, so the 429/503 check above never
                # fires for this class of error. Root-caused 2026-08-17 (Dr. Victor):
                # a single weekly run makes ~30+ back-to-back Gemini calls (7 for new
                # captions, ~14 for image vetting, 14 for the review itself) and several
                # days came back "error, score 0" in creative_review.py even though the
                # 429/503 retry above was already in place — because most of those
                # failures were plain timeouts under load, not explicit rate-limit
                # responses, and timeouts were previously NOT retried at all. Same
                # backoff treatment as 429/503 fixes it.
                last_err = RuntimeError(f"Network error from Gemini (model={model}): {e}")
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                break
        if status_code in (404, 429, 503) or status_code is None:
            # status_code is None here means every attempt hit the network-error
            # branch above (never got as far as an HTTP response) — worth trying
            # the next candidate model too, same as a dead/overloaded model name.
            continue
        raise last_err  # anything else (bad key, bad request, ...) won't fix itself by switching models
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
