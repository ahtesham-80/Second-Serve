import os
import pytest
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, FoodListing, Claim
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def seed_users(app):
    with app.app_context():
        admin = User(
            name="Admin User",
            email="admin@test.org",
            role="ADMIN",
            phone="9876500000",
            organization_name="Admin Org",
            locality="Central",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED"
        )
        admin.set_password("adminpass")

        donor = User(
            name="Donor Ramesh",
            email="donor@test.org",
            role="DONOR",
            phone="9876511111",
            organization_name="Taj Kitchens",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED"
        )
        donor.set_password("donorpass")

        ngo_approved = User(
            name="NGO Approved",
            email="ngo_approved@test.org",
            role="NGO",
            phone="9876522222",
            organization_name="Feeding Hope",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED"
        )
        ngo_approved.set_password("ngopass")

        ngo_pending = User(
            name="NGO Pending",
            email="ngo_pending@test.org",
            role="NGO",
            phone="9876533333",
            organization_name="Care Trust",
            locality="Whitefield",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="PENDING"
        )
        ngo_pending.set_password("ngopass")

        db.session.add_all([admin, donor, ngo_approved, ngo_pending])
        db.session.commit()

        return {
            'admin': admin.id,
            'donor': donor.id,
            'ngo_approved': ngo_approved.id,
            'ngo_pending': ngo_pending.id
        }
