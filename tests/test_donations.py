import pytest
from datetime import datetime, timedelta
from app.models import User, FoodListing
from app.extensions import db
from app.services.listing_service import create_listing, update_listing, cancel_listing, ListingServiceError


def test_create_donation_success(app, seed_users):
    """Test successful donation creation with valid inputs."""
    with app.app_context():
        donor = User.query.get(seed_users['donor'])
        now = datetime.utcnow()
        data = {
            'title': 'Evening Buffet Surplus Meals',
            'category': 'Cooked Meals',
            'description': 'Rice, dal, and fresh vegetables prepared 1 hr ago.',
            'quantity': 35,
            'unit': 'Meals',
            'food_type': 'Vegetarian',
            'location': 'Taj Kitchens Dispatch Door',
            'locality': 'Indiranagar',
            'city': 'Bengaluru',
            'district': 'Bengaluru Urban',
            'available_from': now,
            'collection_deadline': now + timedelta(hours=3)
        }
        listing = create_listing(donor, data)
        assert listing.id is not None
        assert listing.status == 'AVAILABLE'
        assert listing.title == 'Evening Buffet Surplus Meals'
        assert listing.quantity == 35.0


def test_create_donation_invalid_quantity(app, seed_users):
    """Test invalid quantity (0 or negative) is rejected."""
    with app.app_context():
        donor = User.query.get(seed_users['donor'])
        now = datetime.utcnow()
        data = {
            'title': 'Test Meals',
            'category': 'Cooked Meals',
            'description': 'Desc',
            'quantity': -5,
            'location': 'Address',
            'locality': 'Indiranagar',
            'city': 'Bengaluru',
            'district': 'Bengaluru Urban',
            'available_from': now,
            'collection_deadline': now + timedelta(hours=2)
        }
        with pytest.raises(ListingServiceError) as exc:
            create_listing(donor, data)
        assert "Quantity must be a positive number" in str(exc.value)


def test_create_donation_past_deadline_rejected(app, seed_users):
    """Test deadline in the past is rejected."""
    with app.app_context():
        donor = User.query.get(seed_users['donor'])
        now = datetime.utcnow()
        data = {
            'title': 'Past Food',
            'category': 'Cooked Meals',
            'description': 'Desc',
            'quantity': 10,
            'location': 'Address',
            'locality': 'Indiranagar',
            'city': 'Bengaluru',
            'district': 'Bengaluru Urban',
            'available_from': now - timedelta(hours=4),
            'collection_deadline': now - timedelta(hours=1)
        }
        with pytest.raises(ListingServiceError) as exc:
            create_listing(donor, data)
        assert "deadline must be set to a future date" in str(exc.value)


def test_edit_donation_unauthorized(app, seed_users):
    """Test that a non-owner cannot edit a listing."""
    with app.app_context():
        donor = User.query.get(seed_users['donor'])
        other_user = User.query.get(seed_users['ngo_approved'])
        now = datetime.utcnow()
        listing = create_listing(donor, {
            'title': 'My Food',
            'category': 'Cooked Meals',
            'description': 'Desc',
            'quantity': 10,
            'location': 'Address',
            'locality': 'Indiranagar',
            'city': 'Bengaluru',
            'district': 'Bengaluru Urban',
            'available_from': now,
            'collection_deadline': now + timedelta(hours=2)
        })

        with pytest.raises(ListingServiceError) as exc:
            update_listing(listing.id, other_user, {'title': 'Tampered Title'})
        assert "Unauthorized" in str(exc.value)


def test_cancel_donation(app, seed_users):
    """Test cancelling an eligible listing."""
    with app.app_context():
        donor = User.query.get(seed_users['donor'])
        now = datetime.utcnow()
        listing = create_listing(donor, {
            'title': 'To Cancel',
            'category': 'Fruits',
            'description': 'Desc',
            'quantity': 15,
            'location': 'Address',
            'locality': 'Indiranagar',
            'city': 'Bengaluru',
            'district': 'Bengaluru Urban',
            'available_from': now,
            'collection_deadline': now + timedelta(hours=4)
        })

        cancel_listing(listing.id, donor, "Spilled accidentally")
        assert listing.status == 'CANCELLED'
