# AURA — Image Generation Playbook
**Issued by Dr. Victor · Updated 19 Aug 2026 (pipeline v6)**

## Rule change (locked)

The rigid **zero-cost only** rule for content assets is **archived**.

**New rule:**
- Prefer free / already-available tools first.
- Controlled low-cost tools are allowed when free options fail quality.
- Any new account, credit card, or paid API key still requires Founder approval.
- Real Design Infra project photos remain the highest priority and will replace AI concepts as soon as supplied.

## Live pipeline (scripts/fetch_images.py v6)

| Priority | Source | Notes |
|----------|--------|--------|
| 0 | `content/assets/real/` | Founder-supplied project photos → `real_project=True` |
| 1 | Unsplash | If `UNSPLASH_ACCESS_KEY` GitHub secret is set |
| 2 | Openverse + Wikimedia | Strict keyword + Gemini vision filter |
| 3 | Cloudflare Workers AI (Flux) | India mid-premium prompts; always labeled concept |
| 4 | SVG fallback | In `render_cards.mjs` if pool still empty |

Every non-real image is flagged `concept: true` so cards show **Concept visualisation**.

## Mandatory rules for every AI / concept image

1. Caption **must** contain the exact phrase “Concept visualisation” (or Hindi equivalent).
2. Never present AI images as completed Design Infra projects.
3. Prefer Indian mid-premium apartment context: scale, materials (oak, marble, veneer, brass), natural light, Delhi NCR feel.
4. At least one conversion signal still required (price range, timeline, inclusion, warranty, or process) — see CONTENT_GUIDELINES_V2.md.
5. Quality gate before queue: Would a comparison shopper shortlist Design Infra after seeing only this image + caption? If no → rework.

## How to add real project photos (highest impact)

1. Put files in `content/assets/real/` (see README there).
2. Name preferably `living-1.jpg`, `kitchen-1.jpg`, etc.
3. Next weekly run (or manual `workflow_dispatch` job = weekly) will register them.

## Optional upgrade

- Add GitHub secret `UNSPLASH_ACCESS_KEY` for better free modern stock.
- Cloudflare secrets already wired for AI concept fill.

## Quality gate checklist (before any card enters approval queue)

- [ ] Real photo OR honest “Concept visualisation” label present
- [ ] Indian mid-premium context (not Western stock / archival)
- [ ] At least one conversion signal in caption
- [ ] No competitor watermarks or irrelevant historical images
- [ ] Would a serious homeowner shortlist after seeing this?

If any box fails → do not enter the Founder’s approval queue.
