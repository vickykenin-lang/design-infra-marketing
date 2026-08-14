#!/usr/bin/env python3
"""AURA — Image Researcher v2: license-safe real interior photos.
Primary source: Wikimedia Commons (reliable direct downloads, clear licenses).
Fallback: Openverse API thumbnails.
Writes: content/assets/<room>-N.jpg, credits.json, fetch_log.txt (for remote debugging).
Runs inside GitHub Actions (open internet).
"""
import json, os, sys, urllib.parse, urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "content", "assets")
os.makedirs(OUT, exist_ok=True)
CREDITS_PATH = os.path.join(OUT, "credits.json")
LOG_PATH = os.path.join(OUT, "fetch_log.txt")
credits = {}
if os.path.exists(CREDITS_PATH):
    try:
        credits = json.load(open(CREDITS_PATH))
    except Exception:
        credits = {}
LOG = []

def log(msg):
    print(msg)
    LOG.append(str(msg))

HEADERS = {"User-Agent": "DesignInfraAURA/2.0 (https://github.com/vickykenin-lang/design-infra-marketing; marketing bot) python-urllib"}
OK_LICENSES = ("cc0", "pd", "public domain", "no restrictions")
def license_ok(lic):
    l = lic.lower()
    if any(ok in l for ok in OK_LICENSES):
        return True
    # plain CC BY (attribution) is fine; exclude BY-SA/BY-NC/BY-ND variants
    return ("cc by" in l or "cc-by" in l) and not any(x in l for x in ("sa", "nc", "nd"))
BAD_TITLE = ("logo", "icon", "poster", "diagram", "plan", "drawing", "graphic", "map", "chart", "screenshot")

def http_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    return json.load(urllib.request.urlopen(req, timeout=30))

def download(url, path, min_bytes=30_000):
    req = urllib.request.Request(url, headers=HEADERS)
    data = urllib.request.urlopen(req, timeout=60).read()
    if len(data) < min_bytes:
        raise ValueError(f"too small ({len(data)} bytes)")
    open(path, "wb").write(data)
    return len(data)

def wikimedia(query, room, count):
    """Search Wikimedia Commons for freely-licensed photos, download width~1200 versions."""
    saved = 0
    url = ("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": 25,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size",
        "iiurlwidth": 1280}))
    try:
        pages = http_json(url).get("query", {}).get("pages", {})
    except Exception as e:
        log(f"[wikimedia] search failed for '{query}': {e}")
        return 0
    for p in pages.values():
        if saved >= count:
            break
        try:
            ii = p["imageinfo"][0]
            meta = ii.get("extmetadata", {})
            lic = (meta.get("LicenseShortName", {}).get("value") or "").lower()
            if not license_ok(lic):
                continue
            if ii.get("width", 0) < 900 or ii.get("height", 0) < 700:
                continue
            title_l = p.get("title", "").lower()
            if any(b in title_l for b in BAD_TITLE):
                log(f"[wikimedia] reject by title: {p.get('title')}")
                continue
            name = f"{room}-{sum(1 for c in credits.values() if c.get('room')==room)+saved+1}.jpg"
            n = download(ii.get("thumburl") or ii["url"], os.path.join(OUT, name), min_bytes=130_000)
            artist = meta.get("Artist", {}).get("value", "")
            # strip html tags from artist
            import re as _re
            artist = _re.sub(r"<[^>]+>", "", artist)[:60].strip()
            credits[name] = {"title": p.get("title", ""), "creator": artist,
                             "license": lic, "source": ii.get("descriptionurl"),
                             "query": query, "room": room, "provider": "wikimedia"}
            saved += 1
            log(f"[wikimedia] saved {name} ({n//1024}KB) lic='{lic}' by '{artist}'")
        except Exception as e:
            log(f"[wikimedia] skip: {e}")
    return saved

def openverse(query, room, count):
    """Fallback: Openverse cached thumbnails (always downloadable, ~600-800px)."""
    saved = 0
    url = ("https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({
        "q": query, "license": "cc0,pdm,by", "category": "photograph", "page_size": 20}))
    try:
        results = http_json(url).get("results", [])
    except Exception as e:
        log(f"[openverse] search failed for '{query}': {e}")
        return 0
    for r in results:
        if saved >= count:
            break
        try:
            thumb = r.get("thumbnail")
            if not thumb:
                continue
            name = f"{room}-ov-{sum(1 for c in credits.values() if c.get('room')==room)+saved+1}.jpg"
            n = download(thumb, os.path.join(OUT, name), min_bytes=15_000)
            credits[name] = {"title": r.get("title"), "creator": r.get("creator"),
                             "license": r.get("license"), "source": r.get("foreign_landing_url"),
                             "query": query, "room": room, "provider": "openverse"}
            saved += 1
            log(f"[openverse] saved {name} ({n//1024}KB) lic='{r.get('license')}'")
        except Exception as e:
            log(f"[openverse] skip: {e}")
    return saved

JOBS = [
    ("modern living room interior design", "living", 6),
    ("modular kitchen interior", "kitchen", 4),
    ("bedroom interior design", "bedroom", 4),
    ("home office interior", "office", 2),
]

if __name__ == "__main__":
    total = 0
    for query, room, count in JOBS:
        got = wikimedia(query, room, count)
        if got < count:
            got += openverse(query, room, count - got)
        log(f"== {room}: {got}/{count} from '{query}'")
        total += got
    json.dump(credits, open(CREDITS_PATH, "w"), indent=1, ensure_ascii=False)
    open(LOG_PATH, "w").write("\n".join(LOG) + "\n")
    log(f"TOTAL saved this run: {total}; pool now {len(credits)}")
    # CC BY images must show a credit chip on the card; renderer handles via credits.json.
