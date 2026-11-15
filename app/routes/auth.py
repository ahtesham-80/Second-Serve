import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.extensions import db
from app.models import AuditLog, User

auth_bp = Blueprint('auth', __name__)


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in allowed_roles and not current_user.is_admin:
                flash("You do not have permission to access that resource.", "danger")
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def approved_ngo_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role != 'NGO':
            flash("This action is restricted to NGO accounts.", "danger")
            return redirect(url_for('main.index'))
        if current_user.verification_status != 'APPROVED':
            flash("Your NGO account is pending administrative approval. You cannot claim food until approved.", "warning")
            return redirect(url_for('ngo.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('auth/login.html')

        if not user.is_active:
            flash("Your account has been deactivated. Please contact the administrator.", "danger")
            return render_template('auth/login.html')

        login_user(user, remember=remember)

        # Audit log login
        audit = AuditLog(
            user_id=user.id,
            action='USER_LOGIN',
            entity_type='User',
            entity_id=user.id,
            details=f"User {user.email} logged in successfully as {user.role}"
        )
        db.session.add(audit)
        db.session.commit()

        flash(f"Welcome back, {user.name}!", "success")

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)

        # Redirect based on role
        if user.role == 'DONOR':
            return redirect(url_for('donor.dashboard'))
        elif user.role == 'NGO':
            return redirect(url_for('ngo.dashboard'))
        elif user.role == 'ADMIN':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'DONOR').strip().upper()
        phone = request.form.get('phone', '').strip()
        organization_name = request.form.get('organization_name', '').strip()
        address = request.form.get('address', '').strip()
        locality = request.form.get('locality', '').strip()
        city = request.form.get('city', '').strip()
        district = request.form.get('district', '').strip()

        # Input Validations
        errors = []
        if not name:
            errors.append("Full name is required.")
        if not email or '@' not in email:
            errors.append("A valid email address is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if not phone:
            errors.append("Phone number is required.")
        if role not in ['DONOR', 'NGO']:
            errors.append("Invalid account type selected. Choose Food Donor or NGO.")
        if not locality or not city or not district:
            errors.append("Locality, City, and District are required.")

        # Email uniqueness check
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            errors.append("An account with this email address already exists. Please log in.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                'auth/register.html',
                name=name, email=email, role=role, phone=phone,
                organization_name=organization_name, address=address,
                locality=locality, city=city, district=district
            )

        # Set verification status: Donors are APPROVED immediately; NGOs require admin verification (PENDING)
        verification_status = 'APPROVED' if role == 'DONOR' else 'PENDING'

        new_user = User(
            name=name,
            email=email,
            role=role,
            phone=phone,
            organization_name=organization_name or name,
            address=address,
            locality=locality,
            city=city,
            district=district,
            verification_status=verification_status,
            is_active=True
        )
        new_user.set_password(password)

        audit = AuditLog(
            action='USER_REGISTERED',
            entity_type='User',
            details=f"New {role} registered: {email} (Status: {verification_status})"
        )

        db.session.add(new_user)
        db.session.add(audit)
        db.session.commit()

        if role == 'NGO':
            flash("Registration successful! Your NGO account has been submitted for administrative verification. You can log in, but claiming donations requires verification.", "warning")
        else:
            flash("Registration successful! You can now log in to start donating surplus food.", "success")

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    audit = AuditLog(
        user_id=current_user.id,
        action='USER_LOGOUT',
        entity_type='User',
        entity_id=current_user.id,
        details=f"User {current_user.email} logged out"
    )
    db.session.add(audit)
    db.session.commit()

    logout_user()
    flash("You have been safely logged out.", "info")
    return redirect(url_for('auth.login'))
