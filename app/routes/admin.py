import os
import sys

# Ensure project root is in sys.path when executed directly or imported from subdirectories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.extensions import db
from app.models import AuditLog, Claim, FoodListing, User
from app.services.listing_service import (
    ListingServiceError,
    cancel_listing,
    check_and_expire_listings,
)
from app.services.report_service import get_admin_charts_data, get_admin_dashboard_stats

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
def admin_before_request():
    """
    Ensure user is authenticated and possesses the ADMIN role before accessing any admin view.
    """
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    if not current_user.is_admin:
        flash("You do not have permission to access that resource.", "danger")
        return redirect(url_for('main.index'))
    check_and_expire_listings()


@admin_bp.route('/dashboard')
def dashboard():
    stats = get_admin_dashboard_stats()
    charts_data = get_admin_charts_data()

    # Pending NGO approval queue
    pending_ngos = User.query.filter_by(role='NGO', verification_status='PENDING').order_by(User.created_at.desc()).all()

    # Recent activity
    recent_donations = FoodListing.query.order_by(FoodListing.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        charts_data=charts_data,
        pending_ngos=pending_ngos,
        recent_donations=recent_donations,
    )


@admin_bp.route('/ngos')
def ngos():
    status_filter = request.args.get('status', 'ALL').upper()
    query = User.query.filter_by(role='NGO')

    if status_filter != 'ALL':
        query = query.filter_by(verification_status=status_filter)

    ngo_list = query.order_by(User.created_at.desc()).all()
    pending_count = User.query.filter_by(role='NGO', verification_status='PENDING').count()

    return render_template(
        'admin/ngos.html',
        ngos=ngo_list,
        current_filter=status_filter,
        pending_count=pending_count,
    )


@admin_bp.route('/ngos/<int:user_id>/approve', methods=['POST'])
def approve_ngo(user_id):
    user = db.get_or_404(User, user_id)
    if user.role != 'NGO':
        flash("Invalid target: user is not an NGO.", "danger")
        return redirect(url_for('admin.ngos'))

    user.verification_status = 'APPROVED'
    audit = AuditLog(
        user_id=current_user.id,
        action='NGO_APPROVED',
        entity_type='User',
        entity_id=user.id,
        details=f"Admin {current_user.name} approved NGO '{user.organization_name or user.name}'",
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"NGO '{user.organization_name or user.name}' has been APPROVED. They can now claim food donations.", "success")
    redirect_target = request.referrer if request.referrer and request.referrer.startswith(request.host_url) else url_for('admin.ngos')
    return redirect(redirect_target)


@admin_bp.route('/ngos/<int:user_id>/reject', methods=['POST'])
def reject_ngo(user_id):
    user = db.get_or_404(User, user_id)
    if user.role != 'NGO':
        flash("Invalid target: user is not an NGO.", "danger")
        return redirect(url_for('admin.ngos'))

    user.verification_status = 'REJECTED'
    audit = AuditLog(
        user_id=current_user.id,
        action='NGO_REJECTED',
        entity_type='User',
        entity_id=user.id,
        details=f"Admin {current_user.name} rejected NGO '{user.organization_name or user.name}'",
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"NGO '{user.organization_name or user.name}' has been REJECTED.", "warning")
    redirect_target = request.referrer if request.referrer and request.referrer.startswith(request.host_url) else url_for('admin.ngos')
    return redirect(redirect_target)


@admin_bp.route('/users')
def users():
    role_filter = request.args.get('role', 'ALL').upper()
    query = User.query

    if role_filter != 'ALL':
        query = query.filter_by(role=role_filter)

    users_list = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users_list, current_filter=role_filter)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
def toggle_user_status(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own administrator account.", "danger")
        return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    audit = AuditLog(
        user_id=current_user.id,
        action='USER_STATUS_TOGGLED',
        entity_type='User',
        entity_id=user.id,
        details=f"User {user.email} active status set to {user.is_active}",
    )
    db.session.add(audit)
    db.session.commit()

    state_str = "activated" if user.is_active else "deactivated"
    flash(f"User '{user.name}' ({user.email}) has been {state_str}.", "info")
    return redirect(url_for('admin.users'))


@admin_bp.route('/donations')
def donations():
    status_filter = request.args.get('status', 'ALL').upper()
    query = FoodListing.query

    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)

    donations_list = query.order_by(FoodListing.created_at.desc()).all()
    return render_template('admin/donations.html', donations=donations_list, current_filter=status_filter)


@admin_bp.route('/donations/<int:listing_id>/cancel', methods=['POST'])
def cancel_donation(listing_id):
    reason = request.form.get('reason', 'Administrative intervention')
    try:
        cancel_listing(listing_id, current_user, reason)
        flash("Donation cancelled by administrator.", "info")
    except ListingServiceError as e:
        flash(str(e), "danger")
    return redirect(url_for('admin.donations'))


@admin_bp.route('/claims')
def claims():
    status_filter = request.args.get('status', 'ALL').upper()
    query = Claim.query

    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)

    claims_list = query.order_by(Claim.created_at.desc()).all()
    return render_template('admin/claims.html', claims=claims_list, current_filter=status_filter)


if __name__ == '__main__':
    from run import app
    app.run(debug=True)
