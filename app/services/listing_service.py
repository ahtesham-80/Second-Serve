import os
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import AuditLog, Claim, FoodListing, User


class ListingServiceError(Exception):
    pass


ALLOWED_CATEGORIES = [
    'Cooked Meals',
    'Fruits',
    'Vegetables',
    'Bakery Items',
    'Packaged Food',
    'Dairy Products',
    'Other'
]

ALLOWED_UNITS = ['Meals', 'kg', 'Packets', 'Boxes', 'Liters']
ALLOWED_FOOD_TYPES = ['Vegetarian', 'Non-Vegetarian']


def is_allowed_file(filename: str) -> bool:
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'webp', 'gif'})


def save_listing_image(file_storage) -> str:
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_file(file_storage.filename):
        raise ListingServiceError("Invalid file extension. Supported formats: PNG, JPG, JPEG, WEBP, GIF.")
    
    filename = secure_filename(file_storage.filename)
    unique_filename = f"{int(datetime.utcnow().timestamp())}_{filename}"
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'app/static/images/uploads')
    
    saved = False
    try:
        os.makedirs(upload_folder, exist_ok=True)
        upload_path = os.path.join(upload_folder, unique_filename)
        file_storage.save(upload_path)
        saved = True
    except OSError:
        pass

    if not saved:
        try:
            tmp_folder = os.path.join('/tmp', 'uploads')
            os.makedirs(tmp_folder, exist_ok=True)
            file_storage.save(os.path.join(tmp_folder, unique_filename))
        except Exception:
            pass

    return unique_filename


def check_and_expire_listings():
    """
    Scans for all AVAILABLE or RESERVED listings past their collection deadline
    and updates status to EXPIRED.
    """
    now = datetime.utcnow()
    expired_listings = FoodListing.query.filter(
        FoodListing.status.in_(['AVAILABLE', 'RESERVED']),
        FoodListing.collection_deadline <= now
    ).all()

    for item in expired_listings:
        # If it was reserved under a pending claim, reject/cancel that claim as expired
        for c in item.claims.filter(Claim.status == 'PENDING').all():
            c.status = 'CANCELLED'
            c.rejection_reason = 'Expired before collection'
            c.updated_at = now
        item.status = 'EXPIRED'
        item.updated_at = now

    if expired_listings:
        db.session.commit()
    return len(expired_listings)


def create_listing(donor: User, data: dict, image_file=None) -> FoodListing:
    """
    Validates input and creates a new food listing for a donor.
    """
    if not donor.is_donor and not donor.is_admin:
        raise ListingServiceError("Only registered donors can publish food listings.")

    title = (data.get('title') or '').strip()
    category = (data.get('category') or '').strip()
    description = (data.get('description') or '').strip()
    food_type = (data.get('food_type') or 'Vegetarian').strip()
    unit = (data.get('unit') or 'Meals').strip()
    location = (data.get('location') or '').strip()
    locality = (data.get('locality') or '').strip()
    city = (data.get('city') or '').strip()
    district = (data.get('district') or '').strip()

    if not title:
        raise ListingServiceError("Food title is required.")
    if category not in ALLOWED_CATEGORIES:
        raise ListingServiceError(f"Invalid food category '{category}'.")
    if not description:
        raise ListingServiceError("Food description is required.")
    if food_type not in ALLOWED_FOOD_TYPES:
        food_type = 'Vegetarian'
    if unit not in ALLOWED_UNITS:
        unit = 'Meals'
    if not location or not locality or not city or not district:
        raise ListingServiceError("Complete location details (address, locality, city, district) are required.")

    # Quantity validation
    try:
        quantity = float(data.get('quantity'))
        if quantity <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        raise ListingServiceError("Quantity must be a positive number greater than 0.")

    # Datetime validations
    now = datetime.utcnow()
    try:
        avail_str = data.get('available_from')
        if isinstance(avail_str, datetime):
            available_from = avail_str
        else:
            available_from = datetime.fromisoformat(avail_str)
    except Exception:
        available_from = now

    try:
        dead_str = data.get('collection_deadline')
        if isinstance(dead_str, datetime):
            collection_deadline = dead_str
        else:
            collection_deadline = datetime.fromisoformat(dead_str)
    except Exception:
        raise ListingServiceError("A valid collection deadline date and time is required.")

    if collection_deadline <= now:
        raise ListingServiceError("Collection deadline must be set to a future date and time.")

    if collection_deadline <= available_from:
        raise ListingServiceError("Collection deadline must be later than the available-from time.")

    # Handle image upload
    image_filename = None
    if image_file:
        image_filename = save_listing_image(image_file)

    listing = FoodListing(
        donor_id=donor.id,
        title=title,
        category=category,
        description=description,
        quantity=quantity,
        unit=unit,
        food_type=food_type,
        image_filename=image_filename,
        location=location,
        locality=locality,
        city=city,
        district=district,
        available_from=available_from,
        collection_deadline=collection_deadline,
        status='AVAILABLE'
    )

    audit = AuditLog(
        user_id=donor.id,
        action='LISTING_CREATED',
        entity_type='FoodListing',
        details=f"Donation listing created: '{title}' ({quantity:g} {unit})"
    )

    db.session.add(listing)
    db.session.add(audit)
    db.session.commit()
    return listing


def update_listing(listing_id: int, donor: User, data: dict, image_file=None) -> FoodListing:
    """
    Updates an existing food listing if eligible.
    """
    listing = FoodListing.query.get(listing_id)
    if not listing:
        raise ListingServiceError("Listing not found.")

    if listing.donor_id != donor.id and not donor.is_admin:
        raise ListingServiceError("Unauthorized: You can only edit your own listings.")

    if listing.status != 'AVAILABLE':
        raise ListingServiceError(f"Cannot edit a listing that is currently '{listing.status}'. Only AVAILABLE listings can be updated.")

    if listing.is_expired:
        listing.status = 'EXPIRED'
        db.session.commit()
        raise ListingServiceError("This listing has expired and cannot be updated.")

    title = (data.get('title') or '').strip()
    category = (data.get('category') or '').strip()
    description = (data.get('description') or '').strip()
    food_type = (data.get('food_type') or listing.food_type).strip()
    unit = (data.get('unit') or listing.unit).strip()
    location = (data.get('location') or '').strip()
    locality = (data.get('locality') or '').strip()
    city = (data.get('city') or '').strip()
    district = (data.get('district') or '').strip()

    if title:
        listing.title = title
    if category and category in ALLOWED_CATEGORIES:
        listing.category = category
    if description:
        listing.description = description
    if food_type in ALLOWED_FOOD_TYPES:
        listing.food_type = food_type
    if unit in ALLOWED_UNITS:
        listing.unit = unit
    if location:
        listing.location = location
    if locality:
        listing.locality = locality
    if city:
        listing.city = city
    if district:
        listing.district = district

    if data.get('quantity'):
        try:
            qty = float(data['quantity'])
            if qty <= 0:
                raise ValueError()
            listing.quantity = qty
        except (TypeError, ValueError):
            raise ListingServiceError("Quantity must be a positive number.")

    if data.get('collection_deadline'):
        try:
            dead_str = data.get('collection_deadline')
            if isinstance(dead_str, datetime):
                new_deadline = dead_str
            else:
                new_deadline = datetime.fromisoformat(dead_str)
            if new_deadline <= datetime.utcnow():
                raise ListingServiceError("Collection deadline must be in the future.")
            listing.collection_deadline = new_deadline
        except ListingServiceError:
            raise
        except Exception:
            raise ListingServiceError("Invalid collection deadline format.")

    if image_file:
        new_image = save_listing_image(image_file)
        if new_image:
            listing.image_filename = new_image

    listing.updated_at = datetime.utcnow()
    db.session.commit()
    return listing


def cancel_listing(listing_id: int, donor: User, reason: str = None) -> FoodListing:
    """
    Cancels an eligible food listing.
    """
    listing = FoodListing.query.get(listing_id)
    if not listing:
        raise ListingServiceError("Listing not found.")

    if listing.donor_id != donor.id and not donor.is_admin:
        raise ListingServiceError("Unauthorized: You can only cancel your own listings.")

    if listing.status in ['COLLECTED', 'CANCELLED']:
        raise ListingServiceError(f"Listing is already '{listing.status}' and cannot be cancelled.")

    listing.status = 'CANCELLED'
    listing.updated_at = datetime.utcnow()

    # Cancel any pending claims on it
    for claim in listing.claims.filter(Claim.status.in_(['PENDING', 'ACCEPTED', 'READY_FOR_COLLECTION'])).all():
        claim.status = 'CANCELLED'
        claim.rejection_reason = f"Donation cancelled by donor: {reason or 'No reason provided'}"
        claim.updated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=donor.id,
        action='LISTING_CANCELLED',
        entity_type='FoodListing',
        entity_id=listing.id,
        details=f"Listing #{listing.id} '{listing.title}' cancelled by donor"
    )
    db.session.add(audit)
    db.session.commit()
    return listing
