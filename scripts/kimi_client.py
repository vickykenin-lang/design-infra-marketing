"""AURA — shared Kimi (Moonshot AI) REST client, OpenAI-compatible chat API.
Used by customer_review.py as a SECOND, independent AI opinion — a different
underlying model than Gemini, on purpose: two AIs built by different teams are
less likely to share the same blind spot (this is why the Japandi mistake or
the badger-photo mistake are worth double-checking with a second model, not
just trusting one).

Kimi's role here is TEXT-ONLY (hook + caption + hashtags), playing a skeptical
"real customer" persona — deliberately a different lens than Gemini's
expert-designer/marketer persona in creative_review.py.

Needs KIMI_API_KEY as an env var / GitHub Secret. KIMI_API_BASE defaults to the
international Moonshot AI platform; set it to https://api.moonshot.cn/v1 in the
secret's sibling env var if the account was created on the China platform instead.
Fails open (raises, caller decides) if key missing or call errors.
"""
import json, os, urllib.request

API_KEY = os.environ.get("KIMI_API_KEY", "")
API_BASE = os.environ.get("KIMI_API_BASE", "https://api.moonshot.ai/v1")
MODEL = os.environ.get("KIMI_MODEL", "moonshot-v1-8k")


def available():
    return bool(API_KEY)


def ask(prompt, timeout=45):
    if not API_KEY:
        raise RuntimeError("KIMI_API_KEY not set")
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]


def ask_json(prompt, timeout=45):
    txt = ask(prompt, timeout).strip()
    if txt.startswith("```"):
        txt = txt.strip("`")
        if txt.lower().startswith("json"):
            txt = txt[4:]
    return json.loads(txt.strip())
