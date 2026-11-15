from datetime import datetime

from app.extensions import db
from app.models import AuditLog, Claim, FoodListing, User


class ClaimServiceError(Exception):
    pass


def create_claim(listing_id: int, ngo_user: User, notes: str | None = None) -> Claim:
    """
    Submits a claim by an approved NGO on an available food listing.
    Transitions listing from AVAILABLE -> RESERVED.
    """
    if not ngo_user or not ngo_user.is_authenticated:
        raise ClaimServiceError("User must be authenticated to submit a claim.")

    if ngo_user.role != 'NGO':
        raise ClaimServiceError("Only registered NGO accounts can submit food claims.")

    if ngo_user.verification_status != 'APPROVED':
        raise ClaimServiceError("Your NGO account is pending administrative verification. Unapproved NGOs cannot claim food.")

    listing = FoodListing.query.with_for_update().get(listing_id)
    if not listing:
        raise ClaimServiceError("Food listing not found.")

    if listing.status != 'AVAILABLE':
        raise ClaimServiceError(f"Listing is not available for claiming (Current status: {listing.status}).")

    if listing.is_expired:
        listing.status = 'EXPIRED'
        db.session.commit()
        raise ClaimServiceError("This food listing collection deadline has passed and is expired.")

    # Check for existing active claims on this listing
    existing_active = Claim.query.filter(
        Claim.listing_id == listing.id,
        Claim.status.in_(['PENDING', 'ACCEPTED', 'READY_FOR_COLLECTION'])
    ).first()
    if existing_active:
        raise ClaimServiceError("This donation is already reserved by an active claim.")

    # Create claim record
    claim = Claim(
        listing_id=listing.id,
        recipient_id=ngo_user.id,
        status='PENDING',
        notes=notes.strip() if notes else None
    )
    listing.status = 'RESERVED'
    listing.updated_at = datetime.utcnow()

    # Audit log
    audit = AuditLog(
        user_id=ngo_user.id,
        action='CLAIM_SUBMITTED',
        entity_type='Claim',
        details=f"Claim #{listing.id} submitted for '{listing.title}' by {ngo_user.organization_name or ngo_user.name}"
    )

    db.session.add(claim)
    db.session.add(audit)
    db.session.commit()
    return claim


def accept_claim(claim_id: int, donor_user: User) -> Claim:
    """
    Donor accepts a pending claim.
    Transitions claim from PENDING -> ACCEPTED.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ClaimServiceError("Claim record not found.")

    if claim.listing.donor_id != donor_user.id and not donor_user.is_admin:
        raise ClaimServiceError("Unauthorized. Only the food donor or an administrator can accept this claim.")

    if claim.status != 'PENDING':
        raise ClaimServiceError(f"Cannot accept a claim with status '{claim.status}'. Must be PENDING.")

    claim.status = 'ACCEPTED'
    claim.updated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=donor_user.id,
        action='CLAIM_ACCEPTED',
        entity_type='Claim',
        entity_id=claim.id,
        details=f"Claim #{claim.id} accepted by donor {donor_user.name}"
    )
    db.session.add(audit)
    db.session.commit()
    return claim


def reject_claim(claim_id: int, donor_user: User, reason: str | None = None) -> Claim:
    """
    Donor rejects a pending claim.
    Transitions claim from PENDING -> REJECTED.
    Releases listing back to AVAILABLE if not expired.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ClaimServiceError("Claim record not found.")

    if claim.listing.donor_id != donor_user.id and not donor_user.is_admin:
        raise ClaimServiceError("Unauthorized. Only the food donor or an administrator can reject this claim.")

    if claim.status != 'PENDING':
        raise ClaimServiceError(f"Cannot reject a claim that is already '{claim.status}'.")

    claim.status = 'REJECTED'
    claim.rejection_reason = reason.strip() if reason else "Donor declined this claim request."
    claim.updated_at = datetime.utcnow()

    # Release listing
    listing = claim.listing
    if listing.is_expired:
        listing.status = 'EXPIRED'
    else:
        listing.status = 'AVAILABLE'
    listing.updated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=donor_user.id,
        action='CLAIM_REJECTED',
        entity_type='Claim',
        entity_id=claim.id,
        details=f"Claim #{claim.id} rejected by donor: {claim.rejection_reason}"
    )
    db.session.add(audit)
    db.session.commit()
    return claim


def mark_ready_for_collection(claim_id: int, donor_user: User) -> Claim:
    """
    Donor marks the food packed and ready for NGO pickup.
    Transitions claim from ACCEPTED -> READY_FOR_COLLECTION.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ClaimServiceError("Claim record not found.")

    if claim.listing.donor_id != donor_user.id and not donor_user.is_admin:
        raise ClaimServiceError("Unauthorized. Only the food donor or administrator can mark collection readiness.")

    if claim.status != 'ACCEPTED':
        raise ClaimServiceError(f"Cannot mark ready: claim is currently '{claim.status}'. Must be ACCEPTED first.")

    claim.status = 'READY_FOR_COLLECTION'
    claim.updated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=donor_user.id,
        action='CLAIM_READY_FOR_COLLECTION',
        entity_type='Claim',
        entity_id=claim.id,
        details=f"Claim #{claim.id} marked ready for pickup by donor"
    )
    db.session.add(audit)
    db.session.commit()
    return claim


def confirm_collected(claim_id: int, actor_user: User) -> Claim:
    """
    Confirms food has been successfully handed over and collected.
    Can be confirmed by either the Donor or the recipient NGO, or Admin.
    Transitions claim from READY_FOR_COLLECTION (or ACCEPTED) -> COLLECTED.
    Transitions listing from RESERVED -> COLLECTED.
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ClaimServiceError("Claim record not found.")

    is_donor = (claim.listing.donor_id == actor_user.id)
    is_ngo = (claim.recipient_id == actor_user.id)
    is_admin = actor_user.is_admin

    if not (is_donor or is_ngo or is_admin):
        raise ClaimServiceError("Unauthorized to confirm collection for this claim.")

    if claim.status not in ['ACCEPTED', 'READY_FOR_COLLECTION']:
        raise ClaimServiceError(f"Cannot confirm collection for claim in '{claim.status}' state.")

    now = datetime.utcnow()
    claim.status = 'COLLECTED'
    claim.collected_at = now
    claim.updated_at = now

    listing = claim.listing
    listing.status = 'COLLECTED'
    listing.updated_at = now

    audit = AuditLog(
        user_id=actor_user.id,
        action='CLAIM_COLLECTED',
        entity_type='Claim',
        entity_id=claim.id,
        details=f"Claim #{claim.id} successfully completed and verified by {actor_user.name} ({actor_user.role})"
    )
    db.session.add(audit)
    db.session.commit()
    return claim


def cancel_claim(claim_id: int, ngo_user: User, reason: str | None = None) -> Claim:
    """
    NGO cancels a pending claim before it is processed.
    Transitions claim from PENDING -> CANCELLED.
    Releases listing back to AVAILABLE (if not expired).
    """
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ClaimServiceError("Claim record not found.")

    if claim.recipient_id != ngo_user.id and not ngo_user.is_admin:
        raise ClaimServiceError("Unauthorized. Only the claiming NGO or administrator can cancel this claim.")

    if claim.status not in ['PENDING', 'ACCEPTED']:
        raise ClaimServiceError(f"Cannot cancel claim in status '{claim.status}'.")

    claim.status = 'CANCELLED'
    claim.updated_at = datetime.utcnow()
    if reason:
        claim.rejection_reason = f"Cancelled by NGO: {reason}"

    listing = claim.listing
    if listing.is_expired:
        listing.status = 'EXPIRED'
    else:
        listing.status = 'AVAILABLE'
    listing.updated_at = datetime.utcnow()

    audit = AuditLog(
        user_id=ngo_user.id,
        action='CLAIM_CANCELLED',
        entity_type='Claim',
        entity_id=claim.id,
        details=f"Claim #{claim.id} cancelled by NGO {ngo_user.name}"
    )
    db.session.add(audit)
    db.session.commit()
    return claim
