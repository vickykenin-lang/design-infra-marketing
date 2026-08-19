# AURA Image Pipeline V2
**Issued by Dr. Victor · 19 Aug 2026 · Traffic-first**

## Goal
Get traffic first with **good pictures + clear message**.  
Real Design Infra project photos remain the long-term conversion asset; until they are supplied, free high-quality modern images + honest labels drive reach.

## Source priority (new order)

| Priority | Source | When used |
|----------|--------|-----------|
| 1 | **Unsplash** | Primary when `UNSPLASH_ACCESS_KEY` secret is set |
| 2 | Openverse (CC0 / CC-BY photograph) | Fallback |
| 3 | Wikimedia Commons | Last free fallback (strict modern-only filters) |
| 4 | Cloudflare AI concept fill | Only if room pool still thin after free sources |
| 5 | Local SVG illustration | Absolute last resort |

## Non-negotiable visual rules

1. **Modern only** — no archival, historical, B&W, heritage, museum, HABS/HAER, 1900s magazine plates.
2. **Aspirational** — bright, clean, mid-to-premium residential interiors that stop the scroll.
3. **Room match** — image must match the intended room (living / kitchen / bedroom / office / bathroom).
4. **No watermarks or competitor logos**.
5. **Honest label on every non-real-project photo**  
   - Free stock / Unsplash / Openverse / Wikimedia → badge: **Concept visualisation**  
   - AI-generated → badge: **Concept visualisation (AI)**  
   - Real Design Infra project photo (when supplied) → no concept badge; optional location credit.

## What you must add for Unsplash

1. Create a free Unsplash developer app: https://unsplash.com/developers  
2. Copy the Access Key.  
3. Add GitHub secret: `UNSPLASH_ACCESS_KEY`  
   (repo → Settings → Secrets and variables → Actions)

Once the secret exists, the next weekly image run will prefer Unsplash automatically.

## Real project photos (still the highest leverage)

When you are ready, supply photos from `@designinfra.interiors` or the Facebook page.  
Those will be marked `real_project: true` and will take priority over all free sources.

## Files touched by this redesign

- `scripts/fetch_images.py` — Unsplash primary + stricter modern filters + concept flag
- `scripts/render_cards.mjs` — shows Concept visualisation badge on all non-real photos
- `data/CONTENT_GUIDELINES_V2.md` — already requires honest concept labels

## Success metric for this phase

Traffic and engagement (saves, profile visits, link clicks).  
Qualified leads remain the only final business metric; good pictures are the fuel that feeds the funnel.
