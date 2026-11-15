from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='DONOR')  # DONOR, NGO, ADMIN
    phone = db.Column(db.String(25), nullable=False)
    organization_name = db.Column(db.String(150), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    locality = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    
    # NGO verification: PENDING, APPROVED, REJECTED. (Donors and Admins default to APPROVED)
    verification_status = db.Column(db.String(20), nullable=False, default='APPROVED')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    listings = db.relationship('FoodListing', backref='donor', lazy='dynamic', cascade='all, delete-orphan')
    claims = db.relationship('Claim', backref='recipient', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def __init__(
        self,
        name=None,
        email=None,
        password_hash=None,
        role='DONOR',
        phone=None,
        organization_name=None,
        address=None,
        locality=None,
        city=None,
        district=None,
        verification_status='APPROVED',
        is_active=True,
        created_at=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        if name is not None:
            self.name = name
        if email is not None:
            self.email = email
        if password_hash is not None:
            self.password_hash = password_hash
        self.role = role
        if phone is not None:
            self.phone = phone
        self.organization_name = organization_name
        self.address = address
        self.locality = locality
        self.city = city
        self.district = district
        self.verification_status = verification_status
        self.is_active = is_active
        if created_at is not None:
            self.created_at = created_at

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if check_password_hash(self.password_hash, password):
            return True
        if password and check_password_hash(self.password_hash, password.lower()):
            return True
        return False

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def is_donor(self):
        return self.role == 'DONOR'

    @property
    def is_ngo(self):
        return self.role == 'NGO'

    @property
    def is_approved_ngo(self):
        return self.is_ngo and self.verification_status == 'APPROVED'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class FoodListing(db.Model):
    __tablename__ = 'food_listings'

    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Cooked Meals, Fruits, Vegetables, Bakery Items, Packaged Food, Dairy Products, Other
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='Meals')  # Meals, kg, Packets, Boxes, Liters
    food_type = db.Column(db.String(20), nullable=False, default='Vegetarian')  # Vegetarian, Non-Vegetarian
    image_filename = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(255), nullable=False)
    locality = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    available_from = db.Column(db.DateTime, nullable=False)
    collection_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='AVAILABLE')  # AVAILABLE, RESERVED, COLLECTED, CANCELLED, EXPIRED
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    claims = db.relationship('Claim', backref='listing', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(
        self,
        donor_id=None,
        title=None,
        category=None,
        description=None,
        quantity=None,
        unit='Meals',
        food_type='Vegetarian',
        image_filename=None,
        location=None,
        locality=None,
        city=None,
        district=None,
        available_from=None,
        collection_deadline=None,
        status='AVAILABLE',
        created_at=None,
        updated_at=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.donor_id = donor_id
        if title is not None:
            self.title = title
        if category is not None:
            self.category = category
        if description is not None:
            self.description = description
        if quantity is not None:
            self.quantity = float(quantity)
        self.unit = unit
        self.food_type = food_type
        self.image_filename = image_filename
        if location is not None:
            self.location = location
        if locality is not None:
            self.locality = locality
        if city is not None:
            self.city = city
        if district is not None:
            self.district = district
        if available_from is not None:
            self.available_from = available_from
        if collection_deadline is not None:
            self.collection_deadline = collection_deadline
        self.status = status
        if created_at is not None:
            self.created_at = created_at
        if updated_at is not None:
            self.updated_at = updated_at

    @property
    def is_expired(self):
        if self.status in ['COLLECTED', 'CANCELLED']:
            return False
        return datetime.utcnow() > self.collection_deadline

    @property
    def effective_status(self):
        if self.status == 'AVAILABLE' and self.is_expired:
            return 'EXPIRED'
        return self.status

    @property
    def remaining_hours(self):
        now = datetime.utcnow()
        if self.collection_deadline <= now:
            return 0.0
        diff = self.collection_deadline - now
        return diff.total_seconds() / 3600.0

    @property
    def remaining_time_str(self):
        now = datetime.utcnow()
        if self.collection_deadline <= now:
            return 'Expired'
        diff = self.collection_deadline - now
        total_minutes = int(diff.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        if hours > 24:
            days = hours // 24
            rem_hours = hours % 24
            return f'{days}d {rem_hours}h left'
        if hours > 0:
            return f'{hours}h {minutes}m left'
        return f'{minutes}m left'

    @property
    def is_urgent(self):
        return self.effective_status == 'AVAILABLE' and 0 < self.remaining_hours < 2.0

    @property
    def active_claim(self):
        return self.claims.filter(Claim.status.in_(['PENDING', 'ACCEPTED', 'READY_FOR_COLLECTION'])).first()

    def __repr__(self):
        return f'<FoodListing {self.id}: {self.title} ({self.status})>'


class Claim(db.Model):
    __tablename__ = 'claims'

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('food_listings.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='PENDING')  # PENDING, ACCEPTED, READY_FOR_COLLECTION, COLLECTED, REJECTED, CANCELLED
    notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    collected_at = db.Column(db.DateTime, nullable=True)

    def __init__(
        self,
        listing_id=None,
        recipient_id=None,
        status='PENDING',
        notes=None,
        rejection_reason=None,
        created_at=None,
        updated_at=None,
        collected_at=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.listing_id = listing_id
        self.recipient_id = recipient_id
        self.status = status
        self.notes = notes
        self.rejection_reason = rejection_reason
        if created_at is not None:
            self.created_at = created_at
        if updated_at is not None:
            self.updated_at = updated_at
        if collected_at is not None:
            self.collected_at = collected_at

    @property
    def step_number(self):
        steps = {
            'PENDING': 1,
            'ACCEPTED': 2,
            'READY_FOR_COLLECTION': 3,
            'COLLECTED': 4,
            'REJECTED': 0,
            'CANCELLED': 0
        }
        return steps.get(self.status, 0)

    @property
    def is_active(self):
        return self.status in ['PENDING', 'ACCEPTED', 'READY_FOR_COLLECTION']

    def __repr__(self):
        return f'<Claim {self.id} for Listing {self.listing_id} ({self.status})>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __init__(
        self,
        action=None,
        entity_type=None,
        user_id=None,
        entity_id=None,
        details=None,
        created_at=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        if action is not None:
            self.action = action
        if entity_type is not None:
            self.entity_type = entity_type
        self.user_id = user_id
        self.entity_id = entity_id
        self.details = details
        if created_at is not None:
            self.created_at = created_at

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>'
