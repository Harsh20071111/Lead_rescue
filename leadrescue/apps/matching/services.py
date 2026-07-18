from dataclasses import dataclass

from apps.core.choices import BHKChoices
from apps.leads.models import Lead
from apps.properties.models import Property

# ---------------------------------------------------------------------------
# Scoring weights (tune without touching scoring logic)
# ---------------------------------------------------------------------------
WEIGHT_BHK = 0.40
WEIGHT_BUDGET = 0.35
WEIGHT_LOCATION = 0.25

MIN_SCORE_THRESHOLD = 0.3

# Numeric representation of BHK choices for adjacency calculation
_BHK_NUMERIC = {
    BHKChoices.STUDIO: 0,
    BHKChoices.ONE_BHK: 1,
    BHKChoices.TWO_BHK: 2,
    BHKChoices.THREE_BHK: 3,
    BHKChoices.FOUR_BHK: 4,
    BHKChoices.FOUR_PLUS_BHK: 5,
}


@dataclass
class MatchBreakdown:
    matched: bool | str  # True, False, or "partial"
    detail: str


@dataclass
class MatchResult:
    object: Lead | Property
    score: float
    breakdown: dict[str, MatchBreakdown]


# ---------------------------------------------------------------------------
# Individual scoring dimensions
# ---------------------------------------------------------------------------

def _score_bhk(lead_bhk: str | None, property_bhk: str | None) -> tuple[float, MatchBreakdown]:
    """Score BHK match between a lead's preference and a property's BHK."""
    if not lead_bhk or not property_bhk:
        return 0.0, MatchBreakdown(matched=False, detail="BHK not specified")

    lead_num = _BHK_NUMERIC.get(lead_bhk)
    prop_num = _BHK_NUMERIC.get(property_bhk)

    if lead_num is None or prop_num is None:
        return 0.0, MatchBreakdown(matched=False, detail="Unknown BHK value")

    diff = abs(lead_num - prop_num)
    if diff == 0:
        return 1.0, MatchBreakdown(matched=True, detail="Exact BHK match")
    if diff == 1:
        return 0.5, MatchBreakdown(matched="partial", detail="Adjacent BHK (±1)")
    return 0.0, MatchBreakdown(matched=False, detail="BHK does not match")


def _score_budget(
    price: float | None,
    budget_min: float | None,
    budget_max: float | None,
) -> tuple[float, MatchBreakdown]:
    """Score budget match. Skip dimension entirely if lead has no budget set."""
    if price is None:
        return 0.0, MatchBreakdown(matched=False, detail="Property price not set")

    if budget_min is None and budget_max is None:
        return 1.0, MatchBreakdown(matched=True, detail="Budget not specified — skipped")

    price = float(price)
    bmin = float(budget_min) if budget_min is not None else 0
    bmax = float(budget_max) if budget_max is not None else float("inf")

    if bmin <= price <= bmax:
        return 1.0, MatchBreakdown(matched=True, detail="Within budget range")

    # Partial credit: within 15% outside the range
    if price < bmin:
        gap = bmin - price
        tolerance = bmin * 0.15
    else:
        gap = price - bmax
        tolerance = bmax * 0.15 if bmax != float("inf") else 0

    if gap <= tolerance:
        return 0.5, MatchBreakdown(matched="partial", detail="Slightly outside budget (≤15%)")

    return 0.0, MatchBreakdown(matched=False, detail="Outside budget range")


def _score_location(
    preferred_location: str | None,
    property_locality: str | None,
    property_city: str | None,
) -> tuple[float, MatchBreakdown]:
    """Score location match with case-insensitive partial matching."""
    if not preferred_location:
        return 1.0, MatchBreakdown(matched=True, detail="Location preference not specified — skipped")

    pref = preferred_location.strip().lower()
    locality = (property_locality or "").strip().lower()
    city = (property_city or "").strip().lower()

    # Exact match on locality
    if locality and pref == locality:
        return 1.0, MatchBreakdown(matched=True, detail="Exact locality match")

    # Preferred location is contained in locality or vice versa
    if locality and (pref in locality or locality in pref):
        return 1.0, MatchBreakdown(matched=True, detail="Location overlap (partial match)")

    # Exact match on city
    if city and pref == city:
        return 1.0, MatchBreakdown(matched=True, detail="Exact city match")

    # Preferred location contained in city or vice versa
    if city and (pref in city or city in pref):
        return 1.0, MatchBreakdown(matched=True, detail="City overlap (partial match)")

    # Same city but different locality (partial)
    if city and locality and pref.split(",")[0].strip() == locality.split(",")[0].strip():
        return 0.5, MatchBreakdown(matched="partial", detail="Same area, different locality")

    if city and pref.split(",")[0].strip() == city:
        return 0.5, MatchBreakdown(matched="partial", detail="Same city, different locality")

    return 0.0, MatchBreakdown(matched=False, detail="No location match")


# ---------------------------------------------------------------------------
# Combined scoring
# ---------------------------------------------------------------------------

def _compute_score(
    bhk_score: float,
    budget_score: float,
    location_score: float,
) -> float:
    return (
        bhk_score * WEIGHT_BHK
        + budget_score * WEIGHT_BUDGET
        + location_score * WEIGHT_LOCATION
    )


def _score_lead_against_property(lead: Lead, prop: Property) -> MatchResult | None:
    """Score a single lead-property pair. Returns None if below threshold."""
    bhk_score, bhk_breakdown = _score_bhk(lead.preferred_bhk, prop.bhk)
    budget_score, budget_breakdown = _score_budget(prop.price, lead.budget_min, lead.budget_max)
    location_score, location_breakdown = _score_location(
        lead.preferred_location, prop.locality, prop.city
    )

    total = _compute_score(bhk_score, budget_score, location_score)

    if total < MIN_SCORE_THRESHOLD:
        return None

    return MatchResult(
        object=prop,
        score=round(total, 4),
        breakdown={
            "bhk": bhk_breakdown,
            "budget": budget_breakdown,
            "location": location_breakdown,
        },
    )


def _score_property_against_lead(prop: Property, lead: Lead) -> MatchResult | None:
    """Score a single property-lead pair. Returns None if below threshold."""
    bhk_score, bhk_breakdown = _score_bhk(lead.preferred_bhk, prop.bhk)
    budget_score, budget_breakdown = _score_budget(prop.price, lead.budget_min, lead.budget_max)
    location_score, location_breakdown = _score_location(
        lead.preferred_location, prop.locality, prop.city
    )

    total = _compute_score(bhk_score, budget_score, location_score)

    if total < MIN_SCORE_THRESHOLD:
        return None

    return MatchResult(
        object=lead,
        score=round(total, 4),
        breakdown={
            "bhk": bhk_breakdown,
            "budget": budget_breakdown,
            "location": location_breakdown,
        },
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_properties_for_lead(lead: Lead, limit: int = 10, qs=None) -> list[MatchResult]:
    """
    Return ranked Properties matching a Lead's requirements, scoped to
    the Lead's agency, status=AVAILABLE only.
    """
    if qs is None:
        qs = Property.objects.for_agency(lead.agency)
    
    properties = (
        qs.filter(status=Property.PropertyStatus.AVAILABLE)
        .select_related("assigned_agent__user")
    )

    results: list[MatchResult] = []
    for prop in properties:
        result = _score_lead_against_property(lead, prop)
        if result is not None:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def match_leads_for_property(prop: Property, limit: int = 10, qs=None) -> list[MatchResult]:
    """
    Return ranked Leads matching a Property, scoped to the same agency.
    """
    if qs is None:
        qs = Lead.objects.for_agency(prop.agency)
        
    leads = (
        qs.select_related("assigned_agent__user")
    )

    results: list[MatchResult] = []
    for lead in leads:
        result = _score_property_against_lead(prop, lead)
        if result is not None:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]
