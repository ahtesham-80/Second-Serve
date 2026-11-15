import pytest
from app.models import User, FoodListing
from app.services.report_service import get_admin_dashboard_stats


def test_admin_dashboard_statistics(app, seed_users):
    """Test platform statistics calculation from SQLite."""
    with app.app_context():
        stats = get_admin_dashboard_stats()
        assert stats['total_users'] == 4
        assert stats['total_donors'] == 1
        assert stats['total_ngos'] == 2
        assert stats['pending_ngos'] == 1


def test_admin_ngo_approval(client, app, seed_users):
    """Test admin approves pending NGO and verification_status changes to APPROVED."""
    # Login as admin
    client.post('/login', data={'email': 'admin@test.org', 'password': 'adminpass'})

    pending_id = seed_users['ngo_pending']
    response = client.post(f'/admin/ngos/{pending_id}/approve', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        ngo = User.query.get(pending_id)
        assert ngo.verification_status == 'APPROVED'
        assert ngo.is_approved_ngo


def test_admin_ngo_rejection(client, app, seed_users):
    """Test admin rejects NGO."""
    client.post('/login', data={'email': 'admin@test.org', 'password': 'adminpass'})

    pending_id = seed_users['ngo_pending']
    response = client.post(f'/admin/ngos/{pending_id}/reject', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        ngo = User.query.get(pending_id)
        assert ngo.verification_status == 'REJECTED'
        assert not ngo.is_approved_ngo


def test_unauthorized_admin_access_blocked(client, seed_users):
    """Test non-admin users cannot access admin routes."""
    # Log in as Donor
    client.post('/login', data={'email': 'donor@test.org', 'password': 'donorpass'})
    response = client.get('/admin/ngos', follow_redirects=True)
    assert b"You do not have permission" in response.data

    # Log in as NGO
    client.get('/logout')
    client.post('/login', data={'email': 'ngo_approved@test.org', 'password': 'ngopass'})
    response = client.get('/admin/users', follow_redirects=True)
    assert b"You do not have permission" in response.data
