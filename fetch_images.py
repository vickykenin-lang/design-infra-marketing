#!/usr/bin/env python3
"""AURA — Image Researcher: finds license-safe real interior photos via Openverse.
Runs inside GitHub Actions (open internet). Saves images + license credits.
Usage: python scripts/fetch_images.py "modern living room" bedroom kitchen
Output: content/assets/<slug>-N.jpg + content/assets/credits.json
"""
import json, os, re, sys, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "content", "assets")
os.makedirs(OUT, exist_ok=True)
CREDITS_PATH = os.path.join(OUT, "credits.json")
credits = {}
if os.path.exists(CREDITS_PATH):
    credits = json.load(open(CREDITS_PATH))

HEADERS = {"User-Agent": "DesignInfra-AURA/1.0 (marketing automation; contact via GitHub)"}

def fetch(query, room="living", count=4):
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
    url = ("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({
        "q": query, "license": "cc0,pdm,by", "category": "photograph",
        "aspect_ratio": "tall,square", "size": "large", "page_size": 20}))
    req = urllib.request.Request(url, headers=HEADERS)
    results = json.load(urllib.request.urlopen(req, timeout=30)).get("results", [])
    saved = 0
    for r in results:
        if saved >= count:
            break
        try:
            img_url = r.get("url") or ""
            if not img_url:
                continue
            name = f"{slug}-{saved+1}.jpg"
            path = os.path.join(OUT, name)
            data = urllib.request.urlopen(
                urllib.request.Request(img_url, headers=HEADERS), timeout=60).read()
            if len(data) < 40_000:  # skip tiny/broken images
                continue
            open(path, "wb").write(data)
            credits[name] = {
                "title": r.get("title"), "creator": r.get("creator"),
                "license": r.get("license"), "license_url": r.get("license_url"),
                "source": r.get("foreign_landing_url"), "query": query, "room": room}
            saved += 1
            print("saved", name, "|", r.get("license"), "|", r.get("creator"))
        except Exception as e:
            print("skip:", e, file=sys.stderr)
    return saved

DEFAULT_QUERIES = [
    ("modern living room interior India", "living"),
    ("modular kitchen interior design", "kitchen"),
    ("cozy bedroom interior design warm", "bedroom"),
    ("home office interior design", "office"),
]

if __name__ == "__main__":
    # CLI usage: python fetch_images.py "query1" "query2" ...  -> all tagged "living"
    # (weekly workflow calls with no args and uses DEFAULT_QUERIES with proper room tags)
    if len(sys.argv) > 1:
        def infer_room(q):
            ql = q.lower()
            for room in ("kitchen", "bedroom", "office", "bathroom", "balcony"):
                if room in ql:
                    return room
            return "living"
        jobs = [(q, infer_room(q)) for q in sys.argv[1:]]
    else:
        jobs = DEFAULT_QUERIES
    total = sum(fetch(q, room=r) for q, r in jobs)
    json.dump(credits, open(CREDITS_PATH, "w"), indent=1, ensure_ascii=False)
    print(f"total saved: {total}")
    # CC-BY images MUST show credit on the post; renderer reads credits.json for that.
