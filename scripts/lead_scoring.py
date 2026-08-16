#!/usr/bin/env python3
"""AURA — Lead Manager: scoring rubric for inbound leads.

Day 5 build (Dr. Victor, 2026-08-16). Mirrors RIO's documented,
transparent-rubric approach (data/product_scoring_model.md over there) so a
human can always see exactly why a lead scored what it scored -- no black
box, no fabricated confidence.

A lead is a dict with (all optional except name/city, missing fields score
as the documented neutral/zero case -- never guessed):
  name, phone, city, project_type, budget_inr (int or None), message

100-point score, same spirit as RIO's 7-factor model:
  - City fit (is the lead inside Design Infra's actual service area):      25
  - Project type fit (turnkey vs partial/non-turnkey ask):                 25
  - Budget fit (mid-to-premium positioning, turnkey-scale budget):         25
  - Contactability (do we have enough to actually reach them):            15
  - Intent signal (timeline/urgency language in their own message):        10

Priority bands (not a promise of response time -- Vicky/design team decide
actual follow-up, this only orders the queue):
  >=70  HOT   -- same-day follow-up suggested
  40-69 WARM  -- follow-up within 2-3 days suggested
  <40   COLD  -- low priority / nurture
"""
import re

PRIMARY_CITY = "delhi ncr"
EXPANSION_CITIES = {"mumbai", "bengaluru", "bangalore", "hyderabad", "pune",
                     "chennai", "kolkata", "ahmedabad"}

TURNKEY_KEYWORDS = ("turnkey", "full home", "whole home", "entire home",
                     "complete interior", "full house", "office interior",
                     "renovation", "full renovation")
PARTIAL_KEYWORDS = ("kitchen", "wardrobe", "false ceiling", "one room",
                     "single room", "bedroom only", "modular kitchen")

URGENCY_KEYWORDS = ("urgent", "asap", "this month", "next month", "within a month",
                     "soon", "ready to start", "ready to move", "immediately",
                     "jaldi", "turant")

BUDGET_TURNKEY_THRESHOLD_INR = 800_000  # mid-to-premium turnkey floor, per company_profile.json positioning


def _city_score(city: str) -> tuple[int, str]:
    if not city:
        return 0, "no city given"
    c = city.strip().lower()
    if PRIMARY_CITY in c or "delhi" in c or "ncr" in c or "gurugram" in c or "gurgaon" in c or "noida" in c or "faridabad" in c:
        return 25, f"'{city}' is Design Infra's primary base (Delhi NCR)"
    for ec in EXPANSION_CITIES:
        if ec in c:
            return 15, f"'{city}' is a listed expansion-target metro"
    return 0, f"'{city}' is outside the current service area -- flag before any commitment is made"


def _project_type_score(project_type: str, message: str) -> tuple[int, str]:
    text = f"{project_type or ''} {message or ''}".lower()
    if any(k in text for k in TURNKEY_KEYWORDS):
        return 25, "mentions turnkey/full-scope project -- matches Design Infra's actual offering"
    if any(k in text for k in PARTIAL_KEYWORDS):
        return 10, "mentions a single element only (e.g. kitchen/wardrobe) -- Design Infra doesn't take standalone jobs; still worth a call to explore turnkey interest, per company_profile.json's stated funnel strategy"
    return 5, "project type unclear from what was given -- needs a qualifying call, not assumed"


def _budget_score(budget_inr) -> tuple[int, str]:
    if budget_inr is None:
        return 15, "no budget stated -- neutral score, not penalized for an unanswered question"
    try:
        b = int(budget_inr)
    except (TypeError, ValueError):
        return 15, "budget value not parseable -- treated as not stated"
    if b >= BUDGET_TURNKEY_THRESHOLD_INR:
        return 25, f"₹{b:,} clears the mid-to-premium turnkey floor (~₹8L)"
    return 10, f"₹{b:,} is below the typical turnkey floor (~₹8L) -- may still be viable, needs a real quote, not assumed"


def _contactability_score(name: str, phone: str) -> tuple[int, str]:
    has_name = bool(name and name.strip())
    has_phone = bool(phone and re.search(r"\d{7,}", phone))
    if has_name and has_phone:
        return 15, "name and a phone number both given"
    if has_name or has_phone:
        return 8, "only one of name/phone given -- confirm the missing one before following up"
    return 0, "neither a usable name nor phone number given -- cannot be followed up as-is"


def _intent_score(message: str) -> tuple[int, str]:
    if not message:
        return 0, "no message text given"
    text = message.lower()
    if any(k in text for k in URGENCY_KEYWORDS):
        return 10, "message contains timeline/urgency language"
    return 5, "generic inquiry, no explicit timeline mentioned"


def score_lead(lead: dict) -> dict:
    """Returns {score, priority, breakdown: [{factor, points, max, reason}]}."""
    city_pts, city_reason = _city_score(lead.get("city", ""))
    proj_pts, proj_reason = _project_type_score(lead.get("project_type", ""), lead.get("message", ""))
    budget_pts, budget_reason = _budget_score(lead.get("budget_inr"))
    contact_pts, contact_reason = _contactability_score(lead.get("name", ""), lead.get("phone", ""))
    intent_pts, intent_reason = _intent_score(lead.get("message", ""))

    breakdown = [
        {"factor": "City fit", "points": city_pts, "max": 25, "reason": city_reason},
        {"factor": "Project type fit", "points": proj_pts, "max": 25, "reason": proj_reason},
        {"factor": "Budget fit", "points": budget_pts, "max": 25, "reason": budget_reason},
        {"factor": "Contactability", "points": contact_pts, "max": 15, "reason": contact_reason},
        {"factor": "Intent signal", "points": intent_pts, "max": 10, "reason": intent_reason},
    ]
    total = sum(f["points"] for f in breakdown)
    priority = "HOT" if total >= 70 else ("WARM" if total >= 40 else "COLD")
    return {"score": total, "priority": priority, "breakdown": breakdown}


if __name__ == "__main__":
    # quick self-test with a realistic example -- not fabricated, just illustrative
    example = {
        "name": "Rohit Sharma", "phone": "+91 9812345671", "city": "Gurugram",
        "project_type": "3BHK full home interior", "budget_inr": 1200000,
        "message": "Looking to start within a month, ready to move ahead.",
    }
    result = score_lead(example)
    print(result["score"], result["priority"])
    for f in result["breakdown"]:
        print(f" - {f['factor']}: {f['points']}/{f['max']} -- {f['reason']}")
