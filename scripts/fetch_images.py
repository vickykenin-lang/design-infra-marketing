#!/usr/bin/env python3
"""AURA — Image Researcher v4: license-safe real interior photos.
Primary source: Wikimedia Commons (reliable direct downloads, clear licenses).
Fallback: Openverse API thumbnails.
Writes: content/assets/<room>-N.jpg, credits.json, fetch_log.txt (for remote debugging).
Runs inside GitHub Actions (open internet).

v4 changes (after owner feedback: "same image repeats, need more variety"):
  - global title-dedup: a Wikimedia file can only ever be saved once, even across
    different room queries (was previously letting the same photo land in two
    room pools, e.g. one "bedroom" photo also saved as the only "living" photo).
  - much stronger negative-keyword filter (was letting through totally unrelated
    photos like wildlife/animal pictures that happened to contain "home office"
    in an unrelated title, e.g. a UK Home Office policy protest photo).
  - positive-signal check: title must actually look like an interior/room photo.
  - bigger per-room pools so a week's worth of posts doesn't reuse one photo.
"""
import json, os, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import gemini_client

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
SEEN_TITLES = {c.get("title", "") for c in credits.values()}
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
BAD_TITLE = (
    "logo", "icon", "poster", "diagram", "plan", "drawing", "graphic", "map", "chart", "screenshot",
    "badger", "cull", "wildlife", "animal", "bird", "dog", "cat ", "insect", "protest", "demonstration",
    "rally", "march", "politician", "minister", "election", "flag", "portrait", "person", "people",
    "celebrity", "actor", "actress", "car ", "vehicle", "truck", "aircraft", "airport", "street view",
    "exterior", "facade", "church", "temple", "mosque", "cathedral", "stadium", "monument", "statue",
    "coat of arms", "emblem", "signage", "sign board",
)
# at least one of these should appear so we don't accept a random photo that merely
# matched the search keywords in an unrelated caption
GOOD_HINT = (
    "interior", "room", "kitchen", "bedroom", "living", "sofa", "furniture", "decor", "décor",
    "design", "home", "apartment", "flat", "house", "wardrobe", "cabinet", "lighting", "ceiling",
    "renovation", "modular", "office", "study", "dining", "cozy", "cosy",
)
def title_ok(title_l):
    if any(b in title_l for b in BAD_TITLE):
        return False, "bad-keyword"
    if not any(g in title_l for g in GOOD_HINT):
        return False, "no-interior-hint"
    return True, ""

VISION_PROMPT_TMPL = """You are a strict photo-authenticity checker for an interior design marketing team.
Look at this photo. It was searched for under the room category "{room}".
Answer ONLY with compact JSON, no markdown fences: {{"is_real_interior_photo": true/false, "matches_room": true/false, "has_watermark_or_logo": true/false, "reason": "<one short sentence>"}}
Rules: is_real_interior_photo must be false for illustrations, renders that look fake/AI-generated-looking, animals, people as the main subject, protests, exteriors, or anything that is not a genuine photograph of a furnished indoor room. matches_room must be false if the room shown clearly isn't a {room} (e.g. a bedroom photo when room is "living")."""

def vision_check(path, room):
    """Stage-A QA: ask Gemini to actually look at the downloaded photo (title-matching
    alone let a badger photo through once). Fails OPEN (returns True) if Gemini is
    unavailable or errors, so the pipeline still works without a key — the keyword
    filter above is the fallback safety net in that case."""
    if not gemini_client.available():
        return True, "gemini not configured — relying on keyword filter only"
    try:
        img = open(path, "rb").read()
        verdict = gemini_client.ask_json(VISION_PROMPT_TMPL.format(room=room), image_bytes=img, mime="image/jpeg")
        ok = bool(verdict.get("is_real_interior_photo")) and bool(verdict.get("matches_room")) and not verdict.get("has_watermark_or_logo")
        return ok, verdict.get("reason", "")
    except Exception as e:
        return True, f"gemini check failed, allowing through: {e}"

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
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": 50,
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
            title = p.get("title", "")
            if title in SEEN_TITLES:
                log(f"[wikimedia] reject duplicate (already in pool): {title}")
                continue
            ok, reason = title_ok(title.lower())
            if not ok:
                log(f"[wikimedia] reject ({reason}): {title}")
                continue
            name = f"{room}-{sum(1 for c in credits.values() if c.get('room')==room)+saved+1}.jpg"
            path = os.path.join(OUT, name)
            n = download(ii.get("thumburl") or ii["url"], path, min_bytes=130_000)
            vok, vreason = vision_check(path, room)
            if not vok:
                os.remove(path)
                log(f"[wikimedia] reject by Gemini vision check: {title} — {vreason}")
                continue
            artist = meta.get("Artist", {}).get("value", "")
            # strip html tags from artist
            import re as _re
            artist = _re.sub(r"<[^>]+>", "", artist)[:60].strip()
            credits[name] = {"title": title, "creator": artist,
                             "license": lic, "source": ii.get("descriptionurl"),
                             "query": query, "room": room, "provider": "wikimedia"}
            SEEN_TITLES.add(title)
            saved += 1
            log(f"[wikimedia] saved {name} ({n//1024}KB) lic='{lic}' by '{artist}' vision='{vreason}'")
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
            title = r.get("title") or ""
            if title in SEEN_TITLES:
                log(f"[openverse] reject duplicate (already in pool): {title}")
                continue
            ok, reason = title_ok(title.lower())
            if not ok:
                log(f"[openverse] reject ({reason}): {title}")
                continue
            name = f"{room}-ov-{sum(1 for c in credits.values() if c.get('room')==room)+saved+1}.jpg"
            path = os.path.join(OUT, name)
            n = download(thumb, path, min_bytes=15_000)
            vok, vreason = vision_check(path, room)
            if not vok:
                os.remove(path)
                log(f"[openverse] reject by Gemini vision check: {title} — {vreason}")
                continue
            credits[name] = {"title": title, "creator": r.get("creator"),
                             "license": r.get("license"), "source": r.get("foreign_landing_url"),
                             "query": query, "room": room, "provider": "openverse"}
            SEEN_TITLES.add(title)
            saved += 1
            log(f"[openverse] saved {name} ({n//1024}KB) lic='{r.get('license')}' vision='{vreason}'")
        except Exception as e:
            log(f"[openverse] skip: {e}")
    return saved

JOBS = [
    ("modern living room interior design sofa", "living", 10),
    ("living room interior design India", "living", 10),
    ("modular kitchen interior design", "kitchen", 8),
    ("kitchen interior design cabinets", "kitchen", 8),
    ("bedroom interior design wardrobe", "bedroom", 8),
    ("bedroom interior design India", "bedroom", 8),
    ("home office room interior design desk", "office", 6),
    ("study room interior design", "office", 6),
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
