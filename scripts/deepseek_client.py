#!/usr/bin/env python3
"""AURA — shared DeepSeek REST client, OpenAI-compatible chat API.
Used by business_review.py as a THIRD, independent AI opinion — a different
underlying model and lab than both Gemini (creative_review.py) and Kimi
(customer_review.py), on purpose: three AIs built by three different teams
are even less likely to share the same blind spot than two.

DeepSeek's role here is TEXT-ONLY (hook + caption + hashtags), playing a
"comparison-shopping homeowner" persona actively weighing Design Infra
against 2-3 competitor interior design companies — a different lens again
from Gemini's expert-designer/marketer pass and Kimi's ordinary-scroller
gut-reaction pass.

Needs DEEPSEEK_API_KEY as an env var / GitHub Secret. DEEPSEEK_API_BASE
defaults to the standard DeepSeek platform endpoint. Fails open (raises,
caller decides) if key missing or call errors.
"""
import json, os, urllib.error, urllib.request

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_BASE = os.environ.get("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1")
MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")


def available():
    return bool(API_KEY)


def ask(prompt, timeout=45):
    if not API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode(errors="replace")[:300]
        except Exception:
            detail = "(could not read error body)"
        raise RuntimeError(f"HTTP {e.code} from DeepSeek: {detail}") from e
    return data["choices"][0]["message"]["content"]


def ask_json(prompt, timeout=45):
    txt = ask(prompt, timeout).strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:]
    txt = txt.strip()
    try:
        # strict=False: tolerate literal newlines inside string values instead of \n
        return json.loads(txt, strict=False)
    except json.JSONDecodeError:
        start, end = txt.find("{"), txt.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(txt[start:end + 1], strict=False)
        raise
