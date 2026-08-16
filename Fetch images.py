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
import json, os, re, sys, urllib.parse, urllib.request
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
    # v5 additions (post-mortem on the "ancestral house" / "American homes and gardens (1907)"
    # incidents — Aug 2026): archival, heritage-tourism and antique-record photography that a
    # bare "interior/room/house" keyword match was letting straight through.
    "ancestral", "heritage", "tourism", "tourist attraction", "historical", "history museum",
    "archive", "archival", "museum", "vintage", "antique", "sepia", "period room", "period photograph",
    "old photograph", "colonial", "manor house", "castle", "palace", "fort ", "fortress", "shrine",
    "monastery", "abbey", "world's fair", "exposition", "watercolour", "watercolor", "sketch of",
    "engraving", "etching", "lithograph", "postcard", "google art project", "habs ", "haer ",
    "national register of historic places", "listed building", "gun & rifle", "gunmaker",
)
# Wikimedia-specific archival record naming conventions (HABS/HAER survey scans, Flickr-Commons
# bulk book-plate uploads like "American homes and gardens (1907) (<flickrid>).jpg") — these carry
# no descriptive room words at all, just a publication name + a pre-1970 year in parentheses.
BAD_TITLE_PATTERNS = (
    re.compile(r"\b1[6-8]\d{2}\b"),          # any 1600s-1800s year
    re.compile(r"\b19[0-4]\d\b"),            # 1900-1949
    re.compile(r"\bhabs\b|\bhaer\b", re.I),  # Historic American Buildings/Engineering Record
)
# Two tiers: a STRONG hint names an actual room/furnishing type and is trustworthy on its own.
# A WEAK hint (home, house, design, decor...) is common in unrelated titles too (tourism listings,
# real-estate ads, magazine names like "American Homes and Gardens") so it is only accepted when
# at least two distinct weak hints appear together, or alongside a strong hint.
STRONG_HINT = (
    "interior design", "living room", "bedroom", "kitchen", "modular kitchen", "sofa", "wardrobe",
    "cabinet", "dining room", "study room", "home office", "furniture", "cozy", "cosy",
)
WEAK_HINT = (
    "interior", "room", "decor", "décor", "design", "home", "apartment", "flat", "house",
    "lighting", "ceiling", "renovation", "modular", "office", "study", "dining",
)
def _has_word(text_l, word):
    """Substring match for multi-word phrases, but a whole-word regex match for single tokens —
    a naive `word in text` check let 'home' match inside 'homes and gardens' and would let 'design'
    match inside e.g. 'designation'. This is what actually let the archival magazine-plate photos
    and the tourism 'Ancestral House' photo through the old filter."""
    if " " in word:
        return word in text_l
    return re.search(r"\b" + re.escape(word) + r"\b", text_l) is not None

def title_ok(title_l, extra_text_l=""):
    """extra_text_l should fold in Wikimedia Categories/ImageDescription/ObjectName when available —
    those catch off-topic content (tourism, heritage, historical archives) that a generic file
    title alone doesn't mention."""
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
Answer ONLY with compact JSON, no markdown fences: {{"is_real_interior_photo": true/false, "matches_room": true/false, "is_modern_photo": true/false, "has_watermark_or_logo": true/false, "reason": "<one short sentence>"}}
Rules:
- is_real_interior_photo must be false for illustrations, renders that look fake/AI-generated-looking, animals,
  people as the main subject, protests, exteriors, paintings/sketches/engravings, or anything that is not a
  genuine photograph of a furnished indoor room.
- matches_room must be false if the room shown clearly isn't a {room} (e.g. a bedroom photo when room is "living").
- is_modern_photo must be false for black-and-white / sepia / archival-looking photos, antique or heritage-house
  interiors, museum period rooms, tourist/heritage-site photography, or anything that looks like a scan from an
  old book, magazine, or postcard rather than a contemporary photo of a livable modern home. It must also be
  false if the photo is noticeably blurry, out of focus, or too low-quality to represent premium interior work.
- If the image contains dense unrelated body text (e.g. an article/caption baked into the photo itself), treat
  that as a strong signal this is not a clean interior photo and set is_real_interior_photo to false."""

def vision_check(path, room):
    """Stage-A QA: ask Gemini to actually look at the downloaded photo (title-matching
    alone let a badger photo through once, and separately let an "Ancestral House" tourism
    photo and 1900s-magazine archival scans through — see BAD_TITLE_PATTERNS above).

    IMPORTANT: this only fails OPEN (returns True, i.e. lets the image through unchecked) when
    Gemini is not configured at all (no API key) — that is a documented, visible tradeoff, logged
    loudly below. If Gemini IS configured but a specific call errors (rate limit, transient network
    issue, retired model, malformed JSON reply), we now fail CLOSED and reject the image instead of
    silently approving it. The old behavior — fail open on *any* exception, including per-call
    errors mid-run — is what most plausibly let living-1.jpg through: the keyword filter alone is
    not trustworthy enough (see title_ok) to be the sole gate for images it merely couldn't out and
    out disqualify. A rejected-by-error image will simply be attempted again next weekly run
    against a different search result, which is a safe default; letting an unverified image publish
    is not."""
    if not gemini_client.available():
        return True, "gemini not configured — relying on keyword filter only (UNVERIFIED, logged loudly)"
    try:
        img = open(path, "rb").read()
        verdict = gemini_client.ask_json(VISION_PROMPT_TMPL.format(room=room), image_bytes=img, mime="image/jpeg")
        ok = (bool(verdict.get("is_real_interior_photo"))
              and bool(verdict.get("matches_room"))
              and bool(verdict.get("is_modern_photo", True))
              and not verdict.get("has_watermark_or_logo"))
        return ok, verdict.get("reason", "")
    except Exception as e:
        # Fail CLOSED: an errored vision check must not silently become an approval.
        return False, f"gemini check errored — rejecting rather than allowing unverified: {e}"

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
            # Fold in Categories/ObjectName/ImageDescription — the file *title* alone often has
            # no useful words at all (e.g. "American homes and gardens (1907) (<flickrid>).jpg"),
            # but Commons categories reliably say things like "Ancestral houses in the Philippines"
            # or "Tourist attractions in ...", which is exactly the off-topic signal we need.
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
                log(f"[wikimedia] reject by Gemini vision check: {title} — {vreason}")
                continue
            artist = meta.get("Artist", {}).get("value", "")
            # strip html tags from artist
            artist = re.sub(r"<[^>]+>", "", artist)[:60].strip()
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