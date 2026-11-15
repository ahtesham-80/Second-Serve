from datetime import datetime
from typing import Any

from app.models import FoodListing, User

# Configurable Weights (Must sum to 1.0)
CATEGORY_WEIGHT = 0.40
LOCATION_WEIGHT = 0.25
QUANTITY_WEIGHT = 0.20
URGENCY_WEIGHT = 0.15

# Category compatibility mappings
CATEGORY_AFFINITIES = {
    'Cooked Meals': {'Cooked Meals': 100, 'Bakery Items': 70, 'Packaged Food': 70, 'Vegetables': 40, 'Fruits': 40},
    'Fruits': {'Fruits': 100, 'Vegetables': 85, 'Packaged Food': 60, 'Dairy Products': 50},
    'Vegetables': {'Vegetables': 100, 'Fruits': 85, 'Cooked Meals': 60, 'Packaged Food': 50},
    'Bakery Items': {'Bakery Items': 100, 'Cooked Meals': 75, 'Packaged Food': 70, 'Dairy Products': 60},
    'Packaged Food': {'Packaged Food': 100, 'Bakery Items': 75, 'Cooked Meals': 70, 'Dairy Products': 70},
    'Dairy Products': {'Dairy Products': 100, 'Packaged Food': 70, 'Bakery Items': 65},
    'Other': {'Other': 100}
}


def calculate_category_score(ngo: User | None, listing: FoodListing, preferred_category: str | None = None) -> tuple[float, str]:
    """
    Computes Category Compatibility (0 - 100).
    Exact match: 100
    Compatible: 70
    No preference: 50
    Incompatible: 0
    """
    cat = (listing.category or '').strip()
    target_category = preferred_category
    
    # If no explicit preferred_category provided, check NGO's past claim history or profile preferences
    if not target_category and ngo:
        # Check NGO's most recent or frequent claimed category
        recent_claim = ngo.claims.join(FoodListing).order_by(FoodListing.created_at.desc()).first()
        if recent_claim and recent_claim.listing:
            target_category = recent_claim.listing.category

    if not target_category:
        return 50.0, f"Neutral category affinity for '{cat}'"

    if cat.lower() == target_category.lower():
        return 100.0, f"Exact category match ({cat})"

    affinities = CATEGORY_AFFINITIES.get(target_category, {})
    if cat in affinities:
        score = float(affinities[cat])
        return score, f"Compatible category ({cat} aligned with {target_category})"
    
    return 20.0, f"Category mismatch ({cat} vs preferred {target_category})"


def calculate_location_score(ngo: User | None, listing: FoodListing) -> tuple[float, str]:
    """
    Computes Location Compatibility (0 - 100).
    Same locality: 100
    Same city: 80
    Same district: 60
    Different known district: 30
    Unknown location: 40
    """
    if not ngo:
        return 40.0, "Unknown NGO location"

    ngo_locality = (ngo.locality or '').strip().lower()
    ngo_city = (ngo.city or '').strip().lower()
    ngo_district = (ngo.district or '').strip().lower()

    list_locality = (listing.locality or '').strip().lower()
    list_city = (listing.city or '').strip().lower()
    list_district = (listing.district or '').strip().lower()

    if not (ngo_locality or ngo_city or ngo_district):
        return 40.0, "Location details unconfigured on NGO profile"

    if ngo_locality and list_locality and ngo_locality == list_locality:
        return 100.0, f"Same locality ({listing.locality})"

    if ngo_city and list_city and ngo_city == list_city:
        return 80.0, f"Same city ({listing.city})"

    if ngo_district and list_district and ngo_district == list_district:
        return 60.0, f"Same district ({listing.district})"

    if ngo_district and list_district and ngo_district != list_district:
        return 30.0, f"Different district ({listing.district})"

    return 40.0, "General regional compatibility"


def calculate_quantity_score(ngo: User | None, listing: FoodListing, requested_qty: float | None = None) -> tuple[float, str]:
    """
    Computes Quantity Suitability (0 - 100).
    Close match (0.8 - 1.25 ratio): 100
    Surplus meets request (1.25 - 2.0 ratio): 85
    Lower but still useful (0.4 - 0.8 ratio): 60
    Extreme mismatch: 30
    Default without requested_qty: 50
    """
    if requested_qty is None or requested_qty <= 0:
        return 50.0, f"Standard batch quantity ({listing.quantity:g} {listing.unit})"

    avail = float(listing.quantity)
    ratio = avail / requested_qty

    if 0.8 <= ratio <= 1.25:
        return 100.0, f"Ideal quantity match ({listing.quantity:g} {listing.unit} for requested {requested_qty:g})"
    elif 1.25 < ratio <= 2.2:
        return 85.0, f"Sufficient surplus quantity ({listing.quantity:g} {listing.unit})"
    elif 0.4 <= ratio < 0.8:
        return 60.0, f"Partial quantity fulfillment ({listing.quantity:g} of {requested_qty:g} {listing.unit})"
    else:
        return 30.0, f"Significant quantity variance ({listing.quantity:g} {listing.unit} vs {requested_qty:g})"


def calculate_urgency_score(listing: FoodListing) -> tuple[float, str]:
    """
    Computes Deadline Urgency (0 - 100).
    < 2 hours: 100 (critical rescue)
    2–6 hours: 85
    6–12 hours: 70
    12–24 hours: 50
    > 24 hours: 30
    Expired <= 0: 0
    """
    hours = listing.remaining_hours
    if hours <= 0:
        return 0.0, "Expired deadline"
    elif hours < 2.0:
        return 100.0, f"Urgent rescue needed ({listing.remaining_time_str})"
    elif 2.0 <= hours < 6.0:
        return 85.0, f"Expiring soon ({listing.remaining_time_str})"
    elif 6.0 <= hours < 12.0:
        return 70.0, f"Moderate window ({listing.remaining_time_str})"
    elif 12.0 <= hours < 24.0:
        return 50.0, f"Standard window ({listing.remaining_time_str})"
    else:
        return 30.0, f"Extended window ({listing.remaining_time_str})"


def get_match_label(score: float) -> str:
    if score >= 85:
        return "Excellent Match"
    elif score >= 70:
        return "Good Match"
    elif score >= 50:
        return "Moderate Match"
    else:
        return "Low Match"


def calculate_match_score(
    ngo: User | None,
    listing: FoodListing,
    preferred_category: str | None = None,
    requested_qty: float | None = None
) -> dict[str, Any]:
    """
    Calculates composite rule-based match score between an NGO and a FoodListing.
    Returns breakdown and transparent explanation.
    """
    cat_score, cat_exp = calculate_category_score(ngo, listing, preferred_category)
    loc_score, loc_exp = calculate_location_score(ngo, listing)
    qty_score, qty_exp = calculate_quantity_score(ngo, listing, requested_qty)
    urg_score, urg_exp = calculate_urgency_score(listing)

    # Weighted calculation
    composite = (
        (CATEGORY_WEIGHT * cat_score) +
        (LOCATION_WEIGHT * loc_score) +
        (QUANTITY_WEIGHT * qty_score) +
        (URGENCY_WEIGHT * urg_score)
    )
    final_score = int(round(max(0.0, min(100.0, composite))))
    label = get_match_label(final_score)

    # Assemble human-readable explainable reason
    positive_reasons = []
    if cat_score >= 70:
        positive_reasons.append(cat_exp)
    if loc_score >= 60:
        positive_reasons.append(loc_exp)
    if urg_score >= 70:
        positive_reasons.append(urg_exp)
    if qty_score >= 70:
        positive_reasons.append(qty_exp)

    if positive_reasons:
        explanation = f"{label} ({final_score}%): " + " • ".join(positive_reasons)
    else:
        explanation = f"{label} ({final_score}%): Standard listing with baseline regional criteria"

    return {
        'score': final_score,
        'label': label,
        'category_score': round(cat_score, 1),
        'location_score': round(loc_score, 1),
        'quantity_score': round(qty_score, 1),
        'urgency_score': round(urg_score, 1),
        'explanation': explanation,
        'weights': {
            'category': int(CATEGORY_WEIGHT * 100),
            'location': int(LOCATION_WEIGHT * 100),
            'quantity': int(QUANTITY_WEIGHT * 100),
            'urgency': int(URGENCY_WEIGHT * 100),
        }
    }


def get_ranked_recommendations(
    ngo: User,
    listings: list[FoodListing] | None = None,
    preferred_category: str | None = None,
    requested_qty: float | None = None,
    limit: int | None = None
) -> list[tuple[FoodListing, dict[str, Any]]]:
    """
    Filters for available, non-expired listings and ranks them descending by match score.
    """
    now = datetime.utcnow()
    if listings is None:
        listings = FoodListing.query.filter(
            FoodListing.status == 'AVAILABLE',
            FoodListing.collection_deadline > now
        ).all()
    else:
        listings = [l for l in listings if l.status == 'AVAILABLE' and l.collection_deadline > now]

    scored = []
    for l in listings:
        match_info = calculate_match_score(ngo, l, preferred_category, requested_qty)
        scored.append((l, match_info))

    # Sort descending by match score, then ascending by deadline
    scored.sort(key=lambda item: (-item[1]['score'], item[0].collection_deadline))

    if limit:
        return scored[:limit]
    return scored
