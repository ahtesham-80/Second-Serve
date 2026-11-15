import pytest
from datetime import datetime, timedelta
from app.models import User, FoodListing
from app.services.matching import (
    calculate_category_score,
    calculate_location_score,
    calculate_quantity_score,
    calculate_urgency_score,
    calculate_match_score,
    get_ranked_recommendations
)


def test_category_scoring(app, seed_users):
    """Test category scoring: exact match=100, compatible=70/75, default neutral=50."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])
        now = datetime.utcnow()
        listing = FoodListing(
            donor_id=seed_users['donor'],
            title="Rice & Stew",
            category="Cooked Meals",
            description="desc",
            quantity=20,
            unit="Meals",
            food_type="Vegetarian",
            location="loc",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now,
            collection_deadline=now + timedelta(hours=3),
            status="AVAILABLE"
        )

        score_exact, _ = calculate_category_score(ngo, listing, preferred_category="Cooked Meals")
        assert score_exact == 100.0

        score_compat, _ = calculate_category_score(ngo, listing, preferred_category="Bakery Items")
        assert score_compat == 75.0

        score_neutral, _ = calculate_category_score(ngo, listing, preferred_category=None)
        assert score_neutral == 50.0


def test_location_scoring(app, seed_users):
    """Test location scoring: same locality=100, same city=80, same district=60."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])  # Indiranagar, Bengaluru, Bengaluru Urban
        now = datetime.utcnow()

        # Same locality
        l_local = FoodListing(
            donor_id=seed_users['donor'], title="T", category="Cooked Meals", description="D",
            quantity=10, location="L", locality="Indiranagar", city="Bengaluru", district="Bengaluru Urban",
            available_from=now, collection_deadline=now + timedelta(hours=2)
        )
        score_local, _ = calculate_location_score(ngo, l_local)
        assert score_local == 100.0

        # Same city, different locality
        l_city = FoodListing(
            donor_id=seed_users['donor'], title="T", category="Cooked Meals", description="D",
            quantity=10, location="L", locality="Koramangala", city="Bengaluru", district="Bengaluru Urban",
            available_from=now, collection_deadline=now + timedelta(hours=2)
        )
        score_city, _ = calculate_location_score(ngo, l_city)
        assert score_city == 80.0


def test_urgency_scoring(app, seed_users):
    """Test urgency scoring: <2h=100, 2-6h=85, 6-12h=70, 12-24h=50, >24h=30."""
    with app.app_context():
        now = datetime.utcnow()

        l_urgent = FoodListing(
            donor_id=seed_users['donor'], title="T", category="Cooked Meals", description="D",
            quantity=10, location="L", locality="A", city="B", district="C",
            available_from=now, collection_deadline=now + timedelta(hours=1, minutes=30),
            status="AVAILABLE"
        )
        assert calculate_urgency_score(l_urgent)[0] == 100.0

        l_expiring = FoodListing(
            donor_id=seed_users['donor'], title="T", category="Cooked Meals", description="D",
            quantity=10, location="L", locality="A", city="B", district="C",
            available_from=now, collection_deadline=now + timedelta(hours=4),
            status="AVAILABLE"
        )
        assert calculate_urgency_score(l_expiring)[0] == 85.0


def test_composite_formula_calculation(app, seed_users):
    """
    Test composite formula:
    Match Score = 0.40 * Cat + 0.25 * Loc + 0.20 * Qty + 0.15 * Urg
    """
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])
        now = datetime.utcnow()

        # Listing with exact category (100), same locality (100), close quantity (100), < 2h urgency (100)
        perfect_listing = FoodListing(
            donor_id=seed_users['donor'], title="Lunch Surplus", category="Cooked Meals", description="D",
            quantity=50, unit="Meals", location="L", locality="Indiranagar", city="Bengaluru", district="Bengaluru Urban",
            available_from=now, collection_deadline=now + timedelta(hours=1, minutes=45),
            status="AVAILABLE"
        )
        match_result = calculate_match_score(
            ngo, perfect_listing,
            preferred_category="Cooked Meals",
            requested_qty=50
        )

        assert match_result['category_score'] == 100.0
        assert match_result['location_score'] == 100.0
        assert match_result['quantity_score'] == 100.0
        assert match_result['urgency_score'] == 100.0
        assert match_result['score'] == 100
        assert match_result['label'] == 'Excellent Match'
        assert "Explainable" not in match_result['explanation'] or len(match_result['explanation']) > 10


def test_ranking_and_expired_exclusion(app, seed_users):
    """Test ranking returns highest scores first and excludes expired listings."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])
        now = datetime.utcnow()

        # Good match (Indiranagar, 3h deadline)
        l_good = FoodListing(
            donor_id=seed_users['donor'], title="Good Match", category="Cooked Meals", description="D",
            quantity=40, unit="Meals", location="L", locality="Indiranagar", city="Bengaluru", district="Bengaluru Urban",
            available_from=now, collection_deadline=now + timedelta(hours=3),
            status="AVAILABLE"
        )
        # Moderate match (Different city, long deadline)
        l_distant = FoodListing(
            donor_id=seed_users['donor'], title="Distant Match", category="Other", description="D",
            quantity=10, unit="Meals", location="L", locality="Mysuru North", city="Mysuru", district="Mysuru",
            available_from=now, collection_deadline=now + timedelta(hours=30),
            status="AVAILABLE"
        )
        # Expired listing
        l_expired = FoodListing(
            donor_id=seed_users['donor'], title="Expired Listing", category="Cooked Meals", description="D",
            quantity=20, unit="Meals", location="L", locality="Indiranagar", city="Bengaluru", district="Bengaluru Urban",
            available_from=now - timedelta(hours=5), collection_deadline=now - timedelta(hours=1),
            status="AVAILABLE"
        )

        ranked = get_ranked_recommendations(ngo, listings=[l_good, l_distant, l_expired], preferred_category="Cooked Meals")
        assert len(ranked) == 2  # Expired must be excluded!
        assert ranked[0][0].title == "Good Match"
        assert ranked[0][1]['score'] > ranked[1][1]['score']
