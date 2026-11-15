import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Claim, FoodListing
from app.routes.auth import approved_ngo_required, role_required
from app.services.claim_service import (
    ClaimServiceError,
    cancel_claim,
    confirm_collected,
    create_claim,
)
from app.services.listing_service import (
    ALLOWED_CATEGORIES,
    ALLOWED_FOOD_TYPES,
    check_and_expire_listings,
)
from app.services.matching import calculate_match_score, get_ranked_recommendations
from app.services.report_service import get_ngo_dashboard_stats

ngo_bp = Blueprint('ngo', __name__, url_prefix='/ngo')


@ngo_bp.before_request
@login_required
@role_required('NGO')
def before_request():
    check_and_expire_listings()


@ngo_bp.route('/dashboard')
def dashboard():
    stats = get_ngo_dashboard_stats(current_user.id)
    
    # Get top 3 smart recommendations
    recommendations = get_ranked_recommendations(current_user, limit=3)
    
    # Active claims tracker
    active_claims = Claim.query.filter(
        Claim.recipient_id == current_user.id,
        Claim.status.in_(['PENDING', 'ACCEPTED', 'READY_FOR_COLLECTION'])
    ).order_by(Claim.created_at.desc()).all()

    return render_template(
        'ngo/dashboard.html',
        stats=stats,
        recommendations=recommendations,
        active_claims=active_claims
    )


@ngo_bp.route('/discover')
def discover():
    query_text = request.args.get('q', '').strip().lower()
    category = request.args.get('category', 'ALL')
    food_type = request.args.get('food_type', 'ALL')
    location_filter = request.args.get('location', '').strip().lower()
    sort_by = request.args.get('sort_by', 'match')  # 'match', 'deadline', 'newest'

    now = datetime.utcnow()
    query = FoodListing.query.filter(
        FoodListing.status == 'AVAILABLE',
        FoodListing.collection_deadline > now
    )

    if query_text:
        query = query.filter(
            (FoodListing.title.ilike(f'%{query_text}%')) |
            (FoodListing.description.ilike(f'%{query_text}%')) |
            (FoodListing.locality.ilike(f'%{query_text}%')) |
            (FoodListing.city.ilike(f'%{query_text}%'))
        )

    if category != 'ALL':
        query = query.filter_by(category=category)

    if food_type != 'ALL':
        query = query.filter_by(food_type=food_type)

    if location_filter:
        query = query.filter(
            (FoodListing.locality.ilike(f'%{location_filter}%')) |
            (FoodListing.city.ilike(f'%{location_filter}%')) |
            (FoodListing.district.ilike(f'%{location_filter}%'))
        )

    listings = query.all()

    # Calculate match scores for all fetched listings
    scored_items = []
    for l in listings:
        match_info = calculate_match_score(current_user, l)
        scored_items.append((l, match_info))

    # Apply sorting
    if sort_by == 'match':
        scored_items.sort(key=lambda x: -x[1]['score'])
    elif sort_by == 'deadline':
        scored_items.sort(key=lambda x: x[0].collection_deadline)
    elif sort_by == 'newest':
        scored_items.sort(key=lambda x: x[0].created_at, reverse=True)

    return render_template(
        'ngo/discover.html',
        items=scored_items,
        categories=ALLOWED_CATEGORIES,
        food_types=ALLOWED_FOOD_TYPES,
        q=query_text,
        category=category,
        food_type=food_type,
        location=location_filter,
        sort_by=sort_by
    )


@ngo_bp.route('/matches')
def matches():
    """
    Dedicated view for rule-based Smart Food Matching.
    """
    req_qty_param = request.args.get('requested_qty', None)
    req_qty = float(req_qty_param) if req_qty_param and req_qty_param.replace('.', '', 1).isdigit() else None
    pref_cat = request.args.get('preferred_category', None)
    if pref_cat == 'ALL':
        pref_cat = None

    recommendations = get_ranked_recommendations(
        current_user,
        preferred_category=pref_cat,
        requested_qty=req_qty
    )

    return render_template(
        'ngo/matches.html',
        recommendations=recommendations,
        categories=ALLOWED_CATEGORIES,
        selected_category=pref_cat,
        requested_qty=req_qty
    )


@ngo_bp.route('/donations/<int:listing_id>')
def donation_detail(listing_id):
    listing = FoodListing.query.get_or_404(listing_id)
    match_info = calculate_match_score(current_user, listing)
    
    # Check if this NGO has claimed this listing before
    my_claim = Claim.query.filter_by(
        listing_id=listing.id,
        recipient_id=current_user.id
    ).order_by(Claim.created_at.desc()).first()

    return render_template(
        'ngo/donation_detail.html',
        listing=listing,
        match=match_info,
        my_claim=my_claim
    )


@ngo_bp.route('/donations/<int:listing_id>/claim', methods=['POST'])
@approved_ngo_required
def claim(listing_id):
    notes = request.form.get('notes', '')
    try:
        claim_obj = create_claim(listing_id, current_user, notes)
        flash("Food donation claimed successfully! Waiting for the donor to accept your pickup request.", "success")
        return redirect(url_for('ngo.claim_tracker', claim_id=claim_obj.id))
    except ClaimServiceError as e:
        flash(str(e), "danger")
        return redirect(url_for('ngo.donation_detail', listing_id=listing_id))


@ngo_bp.route('/claims')
@ngo_bp.route('/my-claims')
def my_claims():
    status_filter = request.args.get('status', 'ALL').upper()
    query = Claim.query.filter_by(recipient_id=current_user.id)

    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)

    claims_list = query.order_by(Claim.created_at.desc()).all()
    return render_template('ngo/my_claims.html', claims=claims_list, current_filter=status_filter)


@ngo_bp.route('/claims/<int:claim_id>')
def claim_tracker(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    if claim.recipient_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized access to claim tracker.", "danger")
        return redirect(url_for('ngo.my_claims'))

    return render_template('ngo/tracker.html', claim=claim)


@ngo_bp.route('/claims/<int:claim_id>/cancel', methods=['POST'])
def cancel(claim_id):
    reason = request.form.get('reason', '')
    try:
        cancel_claim(claim_id, current_user, reason)
        flash("Your claim has been cancelled.", "info")
    except ClaimServiceError as e:
        flash(str(e), "danger")
    return redirect(url_for('ngo.my_claims'))


@ngo_bp.route('/claims/<int:claim_id>/confirm-collected', methods=['POST'])
def confirm_pickup(claim_id):
    try:
        confirm_collected(claim_id, current_user)
        flash("Collection confirmed! Food successfully rescued and marked as completed.", "success")
    except ClaimServiceError as e:
        flash(str(e), "danger")
    return redirect(url_for('ngo.claim_tracker', claim_id=claim_id))
