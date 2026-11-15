from datetime import datetime

from sqlalchemy import func

from app.extensions import db
from app.models import Claim, FoodListing, User


def get_admin_dashboard_stats():
    """
    Computes genuine platform-wide metrics directly from SQLite.
    """
    total_users = User.query.count()
    total_donors = User.query.filter_by(role='DONOR').count()
    total_ngos = User.query.filter_by(role='NGO').count()
    pending_ngos = User.query.filter_by(role='NGO', verification_status='PENDING').count()

    total_donations = FoodListing.query.count()
    available_donations = FoodListing.query.filter_by(status='AVAILABLE').count()
    reserved_donations = FoodListing.query.filter_by(status='RESERVED').count()
    collected_donations = FoodListing.query.filter_by(status='COLLECTED').count()
    expired_donations = FoodListing.query.filter_by(status='EXPIRED').count()
    cancelled_donations = FoodListing.query.filter_by(status='CANCELLED').count()

    total_claims = Claim.query.count()
    pending_claims = Claim.query.filter_by(status='PENDING').count()
    completed_collections = Claim.query.filter_by(status='COLLECTED').count()

    # Sum of quantity listed vs collected
    total_qty_listed = db.session.query(func.coalesce(func.sum(FoodListing.quantity), 0.0)).scalar() or 0.0
    total_qty_collected = db.session.query(
        func.coalesce(func.sum(FoodListing.quantity), 0.0)
    ).filter(FoodListing.status == 'COLLECTED').scalar() or 0.0

    return {
        'total_users': total_users,
        'total_donors': total_donors,
        'total_ngos': total_ngos,
        'pending_ngos': pending_ngos,
        'total_donations': total_donations,
        'available_donations': available_donations,
        'reserved_donations': reserved_donations,
        'collected_donations': collected_donations,
        'expired_donations': expired_donations,
        'cancelled_donations': cancelled_donations,
        'total_claims': total_claims,
        'pending_claims': pending_claims,
        'completed_collections': completed_collections,
        'total_qty_listed': round(total_qty_listed, 1),
        'total_qty_collected': round(total_qty_collected, 1)
    }


def get_admin_charts_data():
    """
    Computes Chart.js compatible series from SQLite records.
    """
    # 1. Status distribution
    status_counts = db.session.query(
        FoodListing.status, func.count(FoodListing.id)
    ).group_by(FoodListing.status).all()
    status_dict = dict(status_counts)

    status_labels = ['Available', 'Reserved', 'Collected', 'Expired', 'Cancelled']
    status_values = [
        status_dict.get('AVAILABLE', 0),
        status_dict.get('RESERVED', 0),
        status_dict.get('COLLECTED', 0),
        status_dict.get('EXPIRED', 0),
        status_dict.get('CANCELLED', 0)
    ]

    # 2. Category distribution
    cat_counts = db.session.query(
        FoodListing.category, func.count(FoodListing.id)
    ).group_by(FoodListing.category).all()
    cat_labels = [c[0] for c in cat_counts] if cat_counts else ['Cooked Meals', 'Bakery Items', 'Fruits', 'Vegetables']
    cat_values = [c[1] for c in cat_counts] if cat_counts else [0, 0, 0, 0]

    # 3. Monthly rescue volume (last 6 months or all)
    monthly_rescues = db.session.query(
        func.strftime('%Y-%m', FoodListing.created_at).label('month'),
        func.count(FoodListing.id).label('total_listings'),
        func.sum(db.case((FoodListing.status == 'COLLECTED', 1), else_=0)).label('collected_count')
    ).group_by('month').order_by('month').all()

    if monthly_rescues:
        month_labels = [m[0] for m in monthly_rescues]
        listed_per_month = [m[1] for m in monthly_rescues]
        collected_per_month = [m[2] for m in monthly_rescues]
    else:
        month_labels = ['Recent']
        listed_per_month = [0]
        collected_per_month = [0]

    return {
        'status_labels': status_labels,
        'status_values': status_values,
        'category_labels': cat_labels,
        'category_values': cat_values,
        'month_labels': month_labels,
        'listed_per_month': listed_per_month,
        'collected_per_month': collected_per_month
    }


def get_donor_dashboard_stats(donor_id: int):
    """
    Computes dashboard metrics for a specific food donor.
    """
    my_listings = FoodListing.query.filter_by(donor_id=donor_id)
    total_listed = my_listings.count()
    active_available = my_listings.filter_by(status='AVAILABLE').count()
    reserved_active = my_listings.filter_by(status='RESERVED').count()
    completed_rescued = my_listings.filter_by(status='COLLECTED').count()

    # Pending claims needing donor review
    pending_claims_count = Claim.query.join(FoodListing).filter(
        FoodListing.donor_id == donor_id,
        Claim.status == 'PENDING'
    ).count()

    total_meals_saved = db.session.query(
        func.coalesce(func.sum(FoodListing.quantity), 0.0)
    ).filter(
        FoodListing.donor_id == donor_id,
        FoodListing.status == 'COLLECTED'
    ).scalar() or 0.0

    return {
        'total_listed': total_listed,
        'active_available': active_available,
        'reserved_active': reserved_active,
        'completed_rescued': completed_rescued,
        'pending_claims_count': pending_claims_count,
        'total_meals_saved': round(total_meals_saved, 1)
    }


def get_ngo_dashboard_stats(ngo_id: int):
    """
    Computes dashboard metrics for a specific NGO.
    """
    now = datetime.utcnow()
    available_count = FoodListing.query.filter(
        FoodListing.status == 'AVAILABLE',
        FoodListing.collection_deadline > now
    ).count()

    my_claims = Claim.query.filter_by(recipient_id=ngo_id)
    active_claims_count = my_claims.filter(
        Claim.status.in_(['PENDING', 'ACCEPTED', 'READY_FOR_COLLECTION'])
    ).count()
    completed_collections_count = my_claims.filter_by(status='COLLECTED').count()

    total_food_collected = db.session.query(
        func.coalesce(func.sum(FoodListing.quantity), 0.0)
    ).join(Claim, Claim.listing_id == FoodListing.id).filter(
        Claim.recipient_id == ngo_id,
        Claim.status == 'COLLECTED'
    ).scalar() or 0.0

    return {
        'available_count': available_count,
        'active_claims_count': active_claims_count,
        'completed_collections_count': completed_collections_count,
        'total_food_collected': round(total_food_collected, 1)
    }
