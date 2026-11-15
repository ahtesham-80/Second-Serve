import pytest
from app.models import User
from app.extensions import db


def test_user_registration_donor(client, app):
    """Test successful donor registration."""
    response = client.post('/register', data={
        'name': 'New Donor',
        'email': 'newdonor@test.org',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'DONOR',
        'phone': '9876543210',
        'organization_name': 'Donor Eatery',
        'address': 'MG Road',
        'locality': 'Downtown',
        'city': 'Bengaluru',
        'district': 'Bengaluru Urban'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email='newdonor@test.org').first()
        assert user is not None
        assert user.role == 'DONOR'
        assert user.verification_status == 'APPROVED'
        assert user.check_password('password123')


def test_user_registration_ngo_status_pending(client, app):
    """Test NGO registration is created in PENDING verification status."""
    response = client.post('/register', data={
        'name': 'New NGO Leader',
        'email': 'newngo@test.org',
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'NGO',
        'phone': '9876543211',
        'organization_name': 'Shelter Relief Trust',
        'address': 'Outer Ring Road',
        'locality': 'Marathahalli',
        'city': 'Bengaluru',
        'district': 'Bengaluru Urban'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email='newngo@test.org').first()
        assert user is not None
        assert user.role == 'NGO'
        assert user.verification_status == 'PENDING'
        assert not user.is_approved_ngo


def test_duplicate_email_registration_rejected(client, seed_users):
    """Test duplicate email is rejected."""
    response = client.post('/register', data={
        'name': 'Duplicate User',
        'email': 'donor@test.org',  # Already seeded
        'password': 'password123',
        'confirm_password': 'password123',
        'role': 'DONOR',
        'phone': '9876543210',
        'organization_name': 'Duplicate Org',
        'address': 'Road',
        'locality': 'Downtown',
        'city': 'Bengaluru',
        'district': 'Bengaluru Urban'
    }, follow_redirects=True)

    assert b"already exists" in response.data


def test_login_success_and_role_redirect(client, seed_users):
    """Test valid credentials redirect to appropriate dashboard."""
    # Donor login
    resp_donor = client.post('/login', data={
        'email': 'donor@test.org',
        'password': 'donorpass'
    }, follow_redirects=False)
    assert resp_donor.status_code == 302
    assert '/donor/dashboard' in resp_donor.location

    # Logout
    client.get('/logout')

    # NGO login
    resp_ngo = client.post('/login', data={
        'email': 'ngo_approved@test.org',
        'password': 'ngopass'
    }, follow_redirects=False)
    assert resp_ngo.status_code == 302
    assert '/ngo/dashboard' in resp_ngo.location

    # Logout
    client.get('/logout')

    # Admin login
    resp_admin = client.post('/login', data={
        'email': 'admin@test.org',
        'password': 'adminpass'
    }, follow_redirects=False)
    assert resp_admin.status_code == 302
    assert '/admin/dashboard' in resp_admin.location


def test_invalid_login_rejected(client, seed_users):
    """Test invalid credentials are denied."""
    response = client.post('/login', data={
        'email': 'donor@test.org',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert b"Invalid email or password" in response.data


def test_role_access_boundaries(client, seed_users):
    """Ensure users cannot access dashboards belonging to other roles."""
    # Login as Donor
    client.post('/login', data={'email': 'donor@test.org', 'password': 'donorpass'})
    
    # Attempt accessing Admin dashboard
    res_admin = client.get('/admin/dashboard', follow_redirects=True)
    assert b"You do not have permission" in res_admin.data

    # Attempt accessing NGO dashboard
    res_ngo = client.get('/ngo/dashboard', follow_redirects=True)
    assert b"You do not have permission" in res_ngo.data
