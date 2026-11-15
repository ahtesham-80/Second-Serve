import pytest
from datetime import datetime, timedelta
from app.models import User, FoodListing, Claim
from app.extensions import db
from app.services.claim_service import (
    create_claim, accept_claim, reject_claim,
    mark_ready_for_collection, confirm_collected, cancel_claim,
    ClaimServiceError
)


@pytest.fixture
def available_listing(app, seed_users):
    with app.app_context():
        now = datetime.utcnow()
        listing = FoodListing(
            donor_id=seed_users['donor'],
            title="Fresh Rice & Dal",
            category="Cooked Meals",
            description="Prepared recently",
            quantity=30,
            unit="Meals",
            food_type="Vegetarian",
            location="Kitchen",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now,
            collection_deadline=now + timedelta(hours=4),
            status="AVAILABLE"
        )
        db.session.add(listing)
        db.session.commit()
        return listing.id


def test_claim_submission_approved_ngo(app, seed_users, available_listing):
    """Test approved NGO can claim an available food listing."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])
        claim = create_claim(available_listing, ngo, "Arriving in 30 mins")

        assert claim.id is not None
        assert claim.status == 'PENDING'
        assert claim.step_number == 1

        # Check listing was reserved
        listing = FoodListing.query.get(available_listing)
        assert listing.status == 'RESERVED'


def test_claim_submission_unapproved_ngo_rejected(app, seed_users, available_listing):
    """Test pending NGO cannot claim a listing."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_pending'])
        with pytest.raises(ClaimServiceError) as exc:
            create_claim(available_listing, ngo, "Trying to claim")
        assert "pending administrative verification" in str(exc.value)


def test_duplicate_claim_prevention(app, seed_users, available_listing):
    """Test duplicate claim on an already claimed listing is prevented."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])
        create_claim(available_listing, ngo)

        # Attempt claiming again
        with pytest.raises(ClaimServiceError) as exc:
            create_claim(available_listing, ngo)
        assert "not available for claiming" in str(exc.value)


def test_full_collection_workflow_steps(app, seed_users, available_listing):
    """
    Test end-to-end 4-step pipeline:
    1. Claim Submitted (PENDING)
    2. Donor Accepted (ACCEPTED)
    3. Ready for Collection (READY_FOR_COLLECTION)
    4. Collected (COLLECTED)
    """
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])
        donor = User.query.get(seed_users['donor'])

        # Step 1: Submit Claim
        claim = create_claim(available_listing, ngo, "Van dispatched")
        assert claim.status == 'PENDING'
        assert claim.step_number == 1

        # Step 2: Donor Accepts
        accept_claim(claim.id, donor)
        claim_refreshed = Claim.query.get(claim.id)
        assert claim_refreshed.status == 'ACCEPTED'
        assert claim_refreshed.step_number == 2

        # Step 3: Donor Marks Ready
        mark_ready_for_collection(claim.id, donor)
        claim_refreshed = Claim.query.get(claim.id)
        assert claim_refreshed.status == 'READY_FOR_COLLECTION'
        assert claim_refreshed.step_number == 3

        # Step 4: Collection Confirmed
        confirm_collected(claim.id, ngo)
        claim_refreshed = Claim.query.get(claim.id)
        assert claim_refreshed.status == 'COLLECTED'
        assert claim_refreshed.step_number == 4
        assert claim_refreshed.collected_at is not None

        # Check listing also marked COLLECTED
        listing = FoodListing.query.get(available_listing)
        assert listing.status == 'COLLECTED'


def test_reject_claim_releases_listing(app, seed_users, available_listing):
    """Test rejecting a claim releases the food listing back to AVAILABLE."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])
        donor = User.query.get(seed_users['donor'])

        claim = create_claim(available_listing, ngo)
        assert FoodListing.query.get(available_listing).status == 'RESERVED'

        reject_claim(claim.id, donor, "Closing early")
        claim_refreshed = Claim.query.get(claim.id)
        assert claim_refreshed.status == 'REJECTED'
        assert claim_refreshed.rejection_reason == "Closing early"

        # Listing released back to AVAILABLE
        assert FoodListing.query.get(available_listing).status == 'AVAILABLE'


def test_cancel_claim_by_ngo_releases_listing(app, seed_users, available_listing):
    """Test NGO cancelling a pending claim releases the listing back to AVAILABLE."""
    with app.app_context():
        ngo = User.query.get(seed_users['ngo_approved'])

        claim = create_claim(available_listing, ngo)
        cancel_claim(claim.id, ngo, "Vehicle breakdown")

        claim_refreshed = Claim.query.get(claim.id)
        assert claim_refreshed.status == 'CANCELLED'
        assert FoodListing.query.get(available_listing).status == 'AVAILABLE'
