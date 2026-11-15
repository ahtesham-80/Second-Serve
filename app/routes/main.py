from datetime import datetime

from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

from app.models import Claim, FoodListing, User
from app.services.listing_service import check_and_expire_listings

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'DONOR':
            return redirect(url_for('donor.dashboard'))
        elif current_user.role == 'NGO':
            return redirect(url_for('ngo.dashboard'))
        elif current_user.role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))

    return landing()


@main_bp.route('/landing')
def landing():
    check_and_expire_listings()
    now = datetime.utcnow()
    
    # Fetch active available listings with photos for showcase
    featured = (
        FoodListing.query.filter(
            FoodListing.status == 'AVAILABLE',
            FoodListing.collection_deadline > now
        )
        .order_by(FoodListing.created_at.desc())
        .limit(3)
        .all()
    )
    
    available_count = FoodListing.query.filter(
        FoodListing.status == 'AVAILABLE',
        FoodListing.collection_deadline > now
    ).count()

    total_claims = Claim.query.filter_by(status='COLLECTED').count()
    total_ngos = User.query.filter_by(role='NGO', verification_status='APPROVED').count()

    return render_template(
        'landing.html',
        featured_listings=featured,
        available_count=available_count,
        total_claims=total_claims,
        total_ngos=total_ngos
    )
