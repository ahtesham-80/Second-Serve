import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import Claim, FoodListing
from app.routes.auth import role_required
from app.services.claim_service import (
    ClaimServiceError,
    accept_claim,
    confirm_collected,
    mark_ready_for_collection,
    reject_claim,
)
from app.services.listing_service import (
    ALLOWED_CATEGORIES,
    ALLOWED_FOOD_TYPES,
    ALLOWED_UNITS,
    ListingServiceError,
    cancel_listing,
    check_and_expire_listings,
    create_listing,
    update_listing,
)
from app.services.report_service import get_donor_dashboard_stats

donor_bp = Blueprint('donor', __name__, url_prefix='/donor')


@donor_bp.before_request
@login_required
@role_required('DONOR')
def before_request():
    # Automatically expire overdue listings on request
    check_and_expire_listings()


@donor_bp.route('/dashboard')
def dashboard():
    stats = get_donor_dashboard_stats(current_user.id)
    
    # Active available listings
    active_listings = FoodListing.query.filter(
        FoodListing.donor_id == current_user.id,
        FoodListing.status.in_(['AVAILABLE', 'RESERVED'])
    ).order_by(FoodListing.created_at.desc()).limit(5).all()

    # Pending claims needing attention
    pending_claims = Claim.query.join(FoodListing).filter(
        FoodListing.donor_id == current_user.id,
        Claim.status == 'PENDING'
    ).order_by(Claim.created_at.desc()).all()

    return render_template(
        'donor/dashboard.html',
        stats=stats,
        active_listings=active_listings,
        pending_claims=pending_claims
    )


@donor_bp.route('/create', methods=['GET', 'POST'])
@donor_bp.route('/donations/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        try:
            image_file = request.files.get('image')
            listing = create_listing(current_user, request.form, image_file)
            flash(f"Donation listing '{listing.title}' published successfully!", "success")
            return redirect(url_for('donor.my_donations'))
        except ListingServiceError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Unexpected error while saving listing: {e!s}", "danger")

    # Prefill default address from donor profile
    return render_template(
        'donor/create_donation.html',
        categories=ALLOWED_CATEGORIES,
        units=ALLOWED_UNITS,
        food_types=ALLOWED_FOOD_TYPES,
        default_location=current_user.address or '',
        default_locality=current_user.locality or '',
        default_city=current_user.city or '',
        default_district=current_user.district or ''
    )


@donor_bp.route('/my-donations')
def my_donations():
    status_filter = request.args.get('status', 'ALL').upper()
    query = FoodListing.query.filter_by(donor_id=current_user.id)

    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)

    listings = query.order_by(FoodListing.created_at.desc()).all()
    return render_template('donor/my_donations.html', listings=listings, current_filter=status_filter)


@donor_bp.route('/donations/<int:listing_id>/edit', methods=['GET', 'POST'])
def edit(listing_id):
    listing = FoodListing.query.get_or_404(listing_id)
    if listing.donor_id != current_user.id and not current_user.is_admin:
        flash("You do not have permission to edit this listing.", "danger")
        return redirect(url_for('donor.my_donations'))

    if listing.status != 'AVAILABLE':
        flash(f"Cannot edit a listing in '{listing.status}' status.", "warning")
        return redirect(url_for('donor.my_donations'))

    if request.method == 'POST':
        try:
            image_file = request.files.get('image')
            update_listing(listing.id, current_user, request.form, image_file)
            flash("Listing updated successfully!", "success")
            return redirect(url_for('donor.my_donations'))
        except ListingServiceError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"Failed to update listing: {e!s}", "danger")

    return render_template(
        'donor/edit_donation.html',
        listing=listing,
        categories=ALLOWED_CATEGORIES,
        units=ALLOWED_UNITS,
        food_types=ALLOWED_FOOD_TYPES
    )


@donor_bp.route('/donations/<int:listing_id>/cancel', methods=['POST'])
def cancel(listing_id):
    reason = request.form.get('reason', '')
    try:
        cancel_listing(listing_id, current_user, reason)
        flash("Donation listing cancelled.", "info")
    except ListingServiceError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Error cancelling listing: {e!s}", "danger")
    return redirect(url_for('donor.my_donations'))


@donor_bp.route('/claims')
def claims():
    status_filter = request.args.get('status', 'ALL').upper()
    query = Claim.query.join(FoodListing).filter(FoodListing.donor_id == current_user.id)

    if status_filter != 'ALL':
        query = query.filter(Claim.status == status_filter)

    claims_list = query.order_by(Claim.created_at.desc()).all()
    return render_template('donor/claims.html', claims=claims_list, current_filter=status_filter)


@donor_bp.route('/claims/<int:claim_id>')
def claim_detail(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    if claim.listing.donor_id != current_user.id and not current_user.is_admin:
        flash("You do not have permission to view this claim.", "danger")
        return redirect(url_for('donor.claims'))

    return render_template('donor/claim_detail.html', claim=claim)


@donor_bp.route('/claims/<int:claim_id>/accept', methods=['POST'])
def accept(claim_id):
    try:
        accept_claim(claim_id, current_user)
        flash("Claim accepted! The NGO has been notified to proceed with collection.", "success")
    except ClaimServiceError as e:
        flash(str(e), "danger")
    return redirect(url_for('donor.claim_detail', claim_id=claim_id))


@donor_bp.route('/claims/<int:claim_id>/reject', methods=['POST'])
def reject(claim_id):
    reason = request.form.get('reason', '')
    try:
        reject_claim(claim_id, current_user, reason)
        flash("Claim request rejected. The listing has been made available again.", "info")
    except ClaimServiceError as e:
        flash(str(e), "danger")
    return redirect(url_for('donor.claims'))


@donor_bp.route('/claims/<int:claim_id>/ready', methods=['POST'])
def mark_ready(claim_id):
    try:
        mark_ready_for_collection(claim_id, current_user)
        flash("Food marked as Ready for Collection! NGO has been instructed to pick up.", "success")
    except ClaimServiceError as e:
        flash(str(e), "danger")
    return redirect(url_for('donor.claim_detail', claim_id=claim_id))


@donor_bp.route('/claims/<int:claim_id>/collected', methods=['POST'])
def confirm(claim_id):
    try:
        confirm_collected(claim_id, current_user)
        flash("Collection confirmed! Food successfully rescued and marked as completed.", "success")
    except ClaimServiceError as e:
        flash(str(e), "danger")
    return redirect(url_for('donor.claim_detail', claim_id=claim_id))


@donor_bp.route('/history')
def history():
    completed_listings = FoodListing.query.filter(
        FoodListing.donor_id == current_user.id,
        FoodListing.status.in_(['COLLECTED', 'EXPIRED', 'CANCELLED'])
    ).order_by(FoodListing.updated_at.desc()).all()

    stats = get_donor_dashboard_stats(current_user.id)
    return render_template('donor/history.html', listings=completed_listings, stats=stats)
