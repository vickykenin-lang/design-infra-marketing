#!/usr/bin/env python3
"""AURA — Image Researcher v6 (Pipeline V2+, 2026-08-19).

Traffic-first redesign (Dr. Victor):
  0. Real Design Infra project photos in content/assets/real/ (if any)
  1. Unsplash (when UNSPLASH_ACCESS_KEY is set)
  2. Openverse → Wikimedia (strict modern-only + India-aware queries)
  3. Cloudflare AI concept fill (India mid-premium prompts)
  4. Local SVG fallback in render_cards.mjs

Every non-real-project image is saved with concept=True so render_cards.mjs
shows an honest "Concept visualisation" badge. Real photos carry real_project=True.

Writes: content/assets/<room>-N.jpg, credits.json, fetch_log.txt
Runs inside GitHub Actions (open internet).
"""
import json, os, re, sys, shutil, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import gemini_client
import cloudflare_image_client

OUT = os.path.join(os.path.dirname(__file__), "..", "content", "assets")
REAL_DIR = os.path.join(OUT, "real")
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
UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")

def log(msg):
    print(msg)
    LOG.append(str(msg))

HEADERS = {"User-Agent": "DesignInfraAURA/3.0 (https://github.com/vickykenin-lang/design-infra-marketing; marketing bot) python-urllib"}
OK_LICENSES = ("cc0", "pd", "public domain", "no restrictions", "unsplash")
def license_ok(lic):
    l = (lic or "").lower()
    if any(ok in l for ok in OK_LICENSES):
        return True
    return ("cc by" in l or "cc-by" in l) and not any(x in l for x in ("sa", "nc", "nd"))

BAD_TITLE = (
    "logo", "icon", "poster", "diagram", "plan", "drawing", "graphic", "map", "chart", "screenshot",
    "badger", "cull", "wildlife", "animal", "bird", "dog", "cat ", "insect", "protest", "demonstration",
    "rally", "march", "politician", "minister", "election", "flag", "portrait", "person", "people",
    "celebrity", "actor", "actress", "car ", "vehicle", "truck", "aircraft", "airport", "street view",
    "exterior", "facade", "church", "temple", "mosque", "cathedral", "stadium", "monument", "statue",
    "coat of arms", "emblem", "signage", "sign board",
    "ancestral", "heritage", "tourism", "tourist attraction", "historical", "history museum",
    "archive", "archival", "museum", "vintage", "antique", "sepia", "period room", "period photograph",
    "old photograph", "colonial", "manor house", "castle", "palace", "fort ", "fortress", "shrine",
    "monastery", "abbey", "world's fair", "exposition", "watercolour", "watercolor", "sketch of",
    "engraving", "etching", "lithograph", "postcard", "google art project", "habs ", "haer ",
    "national register of historic places", "listed building", "gun & rifle", "gunmaker",
    "ruined", "abandoned", "derelict", "dilapidated", "wreck", "rubble",
    "ship ", "smoking room", "library ceiling", "rotunda", "waiting room",
)
BAD_TITLE_PATTERNS = (
    re.compile(r"\b1[6-8]\d{2}\b"),
    re.compile(r"\b19[0-4]\d\b"),
    re.compile(r"\bhabs\b|\bhaer\b", re.I),
)
STRONG_HINT = (
    "interior design", "living room", "bedroom", "kitchen", "modular kitchen", "sofa", "wardrobe",
    "cabinet", "dining room", "study room", "home office", "furniture", "cozy", "cosy",
    "modern interior", "apartment interior", "contemporary interior", "indian interior",
)
WEAK_HINT = (
    "interior", "room", "decor", "décor", "design", "home", "apartment", "flat", "house",
    "lighting", "ceiling", "renovation", "modular", "office", "study", "dining",
)
def _has_word(text_l, word):
    if " " in word:
        return word in text_l
    return re.search(r"\b" + re.escape(word) + r"\b", text_l) is not None

def title_ok(title_l, extra_text_l=""):
    text = title_l + " " + (extra_text_l or "")
    if any(b in text for b in BAD_TITLE):
        return False, "bad-keyword"
    if any(p.search(text) for p in BAD_TITLE_PATTERNS):
        return False, "bad-keyword-archival"
    if any(_has_word(text, g) for g in STRONG_HINT):
        return True, ""
    weak_hits = sum(1 for g in WEAK_HINT if _has_word(text, g))
    if weak_hits >= 2:
        return True, ""
    return False, "no-interior-hint"

VISION_PROMPT_TMPL = """You are a strict photo-authenticity checker for an interior design marketing team
targeting modern Indian residential clients (Delhi NCR and other metros).
Look at this photo. It was searched for under the room category "{room}".
Answer ONLY with compact JSON, no markdown fences: {{"is_real_interior_photo": true/false, "matches_room": true/false, "is_modern_photo": true/false, "is_aspirational": true/false, "has_watermark_or_logo": true/false, "looks_indian_or_universal_premium": true/false, "reason": "<one short sentence>"}}
Rules:
- is_real_interior_photo must be false for illustrations, obvious fake CGI, animals,
  people as the main subject, protests, exteriors, paintings/sketches/engravings, or anything that is not a
  genuine photograph of a furnished indoor room.
- matches_room must be false if the room shown clearly isn't a {room}.
- is_modern_photo must be false for black-and-white / sepia / archival-looking photos, antique or heritage-house
  interiors, museum period rooms, tourist photography, or anything that looks like a scan from an
  old book or postcard. Also false if blurry or too low-quality for premium marketing.
- is_aspirational must be true only if the space looks bright, clean, and mid-to-premium (something a
  Delhi NCR homeowner would aspire to). Dark, cluttered, or dated interiors fail this check.
- looks_indian_or_universal_premium: true if materials/scale could plausibly appear in a modern Indian
  apartment (oak, marble, veneer, modular, warm lighting). False for strongly Western period rooms,
  US suburban staging with carpet + dated furniture, or ship/library archive interiors.
- If the image contains dense unrelated body text or a competitor watermark, set is_real_interior_photo to false."""

def vision_check(path, room):
    if not gemini_client.available():
        return True, "gemini not configured — relying on keyword filter only (UNVERIFIED)"
    try:
        img = open(path, "rb").read()
        verdict = gemini_client.ask_json(VISION_PROMPT_TMPL.format(room=room), image_bytes=img, mime="image/jpeg")
        ok = (bool(verdict.get("is_real_interior_photo"))
              and bool(verdict.get("matches_room"))
              and bool(verdict.get("is_modern_photo", True))
              and bool(verdict.get("is_aspirational", True))
              and bool(verdict.get("looks_indian_or_universal_premium", True))
              and not verdict.get("has_watermark_or_logo"))
        return ok, verdict.get("reason", "")
    except Exception as e:
        return False, f"gemini check errored — rejecting rather than allowing unverified: {e}"

def http_json(url, extra_headers=None):
    h = dict(HEADERS)
    if extra_headers:
        h.update(extra_headers)
    req = urllib.request.Request(url, headers=h)
    return json.load(urllib.request.urlopen(req, timeout=30))

def download(url, path, min_bytes=30_000):
    req = urllib.request.Request(url, headers=HEADERS)
    data = urllib.request.urlopen(req, timeout=60).read()
    if len(data) < min_bytes:
        raise ValueError(f"too small ({len(data)} bytes)")
    open(path, "wb").write(data)
    return len(data)

def _save_credit(name, title, creator, license_, source, query, room, provider, ai_generated=False, real_project=False):
    credits[name] = {
        "title": title, "creator": creator or "",
        "license": license_ or "", "source": source or "",
        "query": query, "room": room, "provider": provider,
        "concept": not bool(real_project),
        "ai_generated": bool(ai_generated),
        "real_project": bool(real_project),
    }
    SEEN_TITLES.add(title)

def ingest_real_project_photos():
    """Register any files dropped into content/assets/real/ as real Design Infra work.

    Naming convention (recommended):
      living-1.jpg, kitchen-2.jpg, bedroom-1.jpg, bathroom-1.jpg, office-1.jpg
    Or any *.jpg / *.jpeg / *.png / *.webp — room inferred from filename if possible.
    """
    if not os.path.isdir(REAL_DIR):
        log("[real] no content/assets/real/ folder — skip")
        return 0
    saved = 0
    room_keys = ("living", "kitchen", "bedroom", "bathroom", "office", "dining")
    for fn in sorted(os.listdir(REAL_DIR)):
        low = fn.lower()
        if not low.endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        src = os.path.join(REAL_DIR, fn)
        room = "living"
        for rk in room_keys:
            if rk in low:
                room = rk
                break
        dest_name = f"real-{room}-{fn}"
        if dest_name in credits or any(c.get("title") == f"Design Infra project — {fn}" for c in credits.values()):
            log(f"[real] already registered: {fn}")
            continue
        dest = os.path.join(OUT, dest_name)
        try:
            shutil.copy2(src, dest)
            _save_credit(
                dest_name,
                f"Design Infra project — {fn}",
                "Design Infra",
                "owned",
                "content/assets/real/",
                "founder_supply",
                room,
                "real-project",
                ai_generated=False,
                real_project=True,
            )
            saved += 1
            log(f"[real] registered {dest_name} as real_project room={room}")
        except Exception as e:
            log(f"[real] failed {fn}: {e}")
    return saved

def unsplash(query, room, count):
    """Primary source when UNSPLASH_ACCESS_KEY is set. High-quality modern interiors."""
    if not UNSPLASH_KEY:
        log("[unsplash] UNSPLASH_ACCESS_KEY not set — skipping (add GitHub secret to enable)")
        return 0
    saved = 0
    url = ("https://api.unsplash.com/search/photos?" + urllib.parse.urlencode({
        "query": query, "per_page": 20, "orientation": "landscape",
        "content_filter": "high", "order_by": "relevant"}))
    try:
        data = http_json(url, extra_headers={"Authorization": f"Client-ID {UNSPLASH_KEY}"})
        results = data.get("results", [])
    except Exception as e:
        log(f"[unsplash] search failed for '{query}': {e}")
        return 0
    for r in results:
        if saved >= count:
            break
        try:
            title = (r.get("description") or r.get("alt_description") or r.get("id") or "unsplash")[:120]
            if title in SEEN_TITLES:
                log(f"[unsplash] reject duplicate: {title}")
                continue
            ok, reason = title_ok(title.lower())
            if not ok and reason == "bad-keyword":
                log(f"[unsplash] reject ({reason}): {title}")
                continue
            img_url = (r.get("urls") or {}).get("regular") or (r.get("urls") or {}).get("full")
            if not img_url:
                continue
            name = f"{room}-us-{sum(1 for c in credits.values() if c.get('room')==room)+saved+1}.jpg"
            path = os.path.join(OUT, name)
            n = download(img_url, path, min_bytes=40_000)
            vok, vreason = vision_check(path, room)
            if not vok:
                os.remove(path)
                log(f"[unsplash] reject by Gemini vision: {title} — {vreason}")
                continue
            user = (r.get("user") or {}).get("name") or "Unsplash"
            source = (r.get("links") or {}).get("html") or "https://unsplash.com"
            _save_credit(name, title, user, "unsplash", source, query, room, "unsplash")
            saved += 1
            log(f"[unsplash] saved {name} ({n//1024}KB) by '{user}' vision='{vreason}'")
        except Exception as e:
            log(f"[unsplash] skip: {e}")
    return saved

def wikimedia(query, room, count):
    saved = 0
    url = ("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6, "gsrlimit": 40,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1280}))
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
                log(f"[wikimedia] reject duplicate: {title}")
                continue
            extra_bits = []
            for f in ("Categories", "ObjectName", "ImageDescription"):
                v = (meta.get(f, {}) or {}).get("value") or ""
                extra_bits.append(re.sub(r"<[^>]+>", " ", v))
            extra_text = " ".join(extra_bits).lower()
            ok, reason = title_ok(title.lower(), extra_text)
            if not ok:
                log(f"[wikimedia] reject ({reason}): {title}")
                continue
            name = f"{room}-{sum(1 for c in credits.values() if c.get('room')==room)+saved+1}.jpg"
            path = os.path.join(OUT, name)
            n = download(ii.get("thumburl") or ii["url"], path, min_bytes=130_000)
            vok, vreason = vision_check(path, room)
            if not vok:
                os.remove(path)
                log(f"[wikimedia] reject by Gemini vision: {title} — {vreason}")
                continue
            artist = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", ""))[:60].strip()
            _save_credit(name, title, artist, lic, ii.get("descriptionurl"), query, room, "wikimedia")
            saved += 1
            log(f"[wikimedia] saved {name} ({n//1024}KB) lic='{lic}' vision='{vreason}'")
        except Exception as e:
            log(f"[wikimedia] skip: {e}")
    return saved

def openverse(query, room, count):
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
                log(f"[openverse] reject duplicate: {title}")
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
                log(f"[openverse] reject by Gemini vision: {title} — {vreason}")
                continue
            _save_credit(name, title, r.get("creator"), r.get("license"), r.get("foreign_landing_url"), query, room, "openverse")
            saved += 1
            log(f"[openverse] saved {name} ({n//1024}KB) vision='{vreason}'")
        except Exception as e:
            log(f"[openverse] skip: {e}")
    return saved

# India mid-premium prompts — aligned with IMAGE_GENERATION_PLAYBOOK.md
AI_PROMPT_BY_ROOM = {
    "living": (
        "Photorealistic modern mid-premium living room in a Delhi NCR apartment, "
        "warm oak and marble finishes, soft natural daylight, clean contemporary Indian aesthetic, "
        "sofa and coffee table, no people, no text, no watermark, architectural photography, 4k"
    ),
    "kitchen": (
        "Photorealistic modern Indian modular kitchen in a Delhi NCR apartment, "
        "sleek cabinetry, warm ambient lighting, marble or quartz countertop, "
        "no people, no text, no watermark, architectural photography, 4k"
    ),
    "bedroom": (
        "Photorealistic modern mid-premium master bedroom in a Delhi NCR apartment, "
        "warm oak wardrobe, soft bedding, natural light, calm contemporary Indian aesthetic, "
        "no people, no text, no watermark, architectural photography, 4k"
    ),
    "office": (
        "Photorealistic modern home office in a Delhi NCR apartment, "
        "clean desk, warm natural light, bookshelf or paneling, mid-premium Indian residential style, "
        "no people, no text, no watermark, architectural photography, 4k"
    ),
    "bathroom": (
        "Photorealistic modern mid-premium bathroom in a Delhi NCR apartment, "
        "clean tiling, quality fixtures, warm lighting, contemporary Indian residential style, "
        "no people, no text, no watermark, architectural photography, 4k"
    ),
}

def ai_concept_fill(room, count):
    if not cloudflare_image_client.available():
        log(f"[cloudflare-ai] not configured — skipping AI fill for {room}")
        return 0
    prompt = AI_PROMPT_BY_ROOM.get(room, AI_PROMPT_BY_ROOM["living"])
    saved = 0
    for _ in range(count):
        try:
            img_bytes = cloudflare_image_client.generate(prompt)
            existing = sum(1 for c in credits.values() if c.get("room") == room)
            name = f"{room}-ai-{existing + 1}.jpg"
            path = os.path.join(OUT, name)
            open(path, "wb").write(img_bytes)
            _save_credit(name, f"AI concept visualisation — {room}", "", "", "", prompt, room, "cloudflare-ai", ai_generated=True)
            saved += 1
            log(f"[cloudflare-ai] generated {name}")
        except Exception as e:
            log(f"[cloudflare-ai] failed for {room}: {e}")
            break
    return saved

# India-first + modern residential queries (v6)
JOBS = [
    ("modern living room interior India apartment", "living", 6),
    ("contemporary living room warm wood marble", "living", 6),
    ("modern modular kitchen India interior", "kitchen", 6),
    ("modern kitchen cabinets warm lighting", "kitchen", 6),
    ("modern bedroom interior wardrobe India", "bedroom", 6),
    ("cozy modern bedroom natural light apartment", "bedroom", 6),
    ("modern home office desk apartment interior", "office", 5),
    ("modern study room interior residential", "office", 4),
    ("modern bathroom interior design apartment", "bathroom", 4),
]

MIN_POOL_PER_ROOM = 4

if __name__ == "__main__":
    total = 0

    # 0) Founder-supplied real project photos first
    total += ingest_real_project_photos()

    rooms_seen = []
    for query, room, count in JOBS:
        got = unsplash(query, room, count)
        if got < count:
            got += openverse(query, room, count - got)
        if got < count:
            got += wikimedia(query, room, count - got)
        log(f"== {room}: {got}/{count} from '{query}'")
        total += got
        if room not in rooms_seen:
            rooms_seen.append(room)

    for room in rooms_seen:
        have = sum(1 for c in credits.values() if c.get("room") == room)
        shortfall = max(0, MIN_POOL_PER_ROOM - have)
        if shortfall:
            total += ai_concept_fill(room, shortfall)

    json.dump(credits, open(CREDITS_PATH, "w"), indent=1, ensure_ascii=False)
    open(LOG_PATH, "w").write("\n".join(LOG) + "\n")
    log(f"TOTAL saved this run: {total}; pool now {len(credits)}")
