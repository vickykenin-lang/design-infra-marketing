#!/usr/bin/env python3
"""AURA — shared Cloudflare Workers AI image-generation client.
Used by fetch_images.py as a THIRD image source, only after Wikimedia and
Openverse together come up short for a room this run. Unlike the first two
(real licensed photographs), this generates a genuine AI concept image —
which is exactly what the brand's "Concept visualisation" labeling rule
(brand/BRAND.md) exists for: honest about being AI-generated, never passed
off as a real project photo. render_cards.mjs shows a distinct on-card badge
for anything this client produces (see credits.json's "ai_generated" flag).

Model: @cf/black-forest-labs/flux-1-schnell. Cloudflare Workers AI's free
tier is 10,000 Neurons/day; this model costs roughly 5-10 Neurons per image
(512x512-class tile pricing), so the daily allowance covers far more than a
single weekly run needs — a handful of concept images, not the primary
source of AURA's imagery.

Needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN as env vars / GitHub
Secrets. Fails open (raises, caller decides) if either is missing or a call
errors — the caller (fetch_images.py) must not let this block the pipeline;
if nothing is available, the existing local SVG illustration fallback in
render_cards.mjs still catches the room, same as before this client existed.
"""
import base64, json, os, urllib.error, urllib.request

ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN", "")
MODEL = os.environ.get("CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")


def available():
    return bool(ACCOUNT_ID and API_TOKEN)


def generate(prompt, steps=8, timeout=60):
    """Returns raw JPEG/PNG bytes for the generated image. Raises on any failure —
    caller decides how to fail open (see ai_concept_fill in fetch_images.py)."""
    if not available():
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN not set")
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/{MODEL}"
    # steps: diffusion step count for flux-1-schnell, max 8 (higher = better quality,
    # slower). 8 is the model's own ceiling, not an arbitrary choice.
    body = json.dumps({"prompt": prompt, "steps": min(max(steps, 1), 8)}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_TOKEN}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode(errors="replace")[:300]
        except Exception:
            detail = "(could not read error body)"
        raise RuntimeError(f"HTTP {e.code} from Cloudflare Workers AI: {detail}") from e
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise RuntimeError(f"Network error from Cloudflare Workers AI: {e}") from e
    if not data.get("success"):
        raise RuntimeError(f"Cloudflare Workers AI call failed: {data.get('errors')}")
    b64 = (data.get("result") or {}).get("image")
    if not b64:
        raise RuntimeError(f"Cloudflare Workers AI: no image in response: {data}")
    return base64.b64decode(b64)
