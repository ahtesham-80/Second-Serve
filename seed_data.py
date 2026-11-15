import os
from datetime import datetime, timedelta
from app import create_app
from app.extensions import db
from app.models import User, FoodListing, Claim, AuditLog


def seed_database():
    app = create_app()
    with app.app_context():
        # Recreate tables cleanly
        db.create_all()

        # Check if already seeded
        if User.query.filter_by(email='admin@secondserve.org').first():
            print("Database already contains seed accounts. Skipping initialization.")
            return

        print("Seeding Second Serve initial demo accounts and realistic sample records...")

        # 1. Administrators
        admin = User(
            name="System Administrator",
            email="admin@secondserve.org",
            role="ADMIN",
            phone="+91 98765 00001",
            organization_name="Second Serve Operations Core",
            address="Civic Center Complex, MG Road",
            locality="Central District",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED",
            is_active=True
        )
        admin.set_password("admin123")
        db.session.add(admin)

        # 2. Donors
        donor1 = User(
            name="Chef Ramesh Sharma",
            email="donor@tajkitchens.com",
            role="DONOR",
            phone="+91 98765 11001",
            organization_name="Taj Grand Kitchens",
            address="100 Feet Road, Stage 2, Indiranagar",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED",
            is_active=True
        )
        donor1.set_password("donor123")
        db.session.add(donor1)

        donor2 = User(
            name="Prof. Meera K.",
            email="canteen@citycollege.edu",
            role="DONOR",
            phone="+91 98765 11002",
            organization_name="City College Central Canteen",
            address="80 Feet Road, 4th Block, Koramangala",
            locality="Koramangala",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED",
            is_active=True
        )
        donor2.set_password("donor123")
        db.session.add(donor2)

        # 3. NGOs
        ngo_approved = User(
            name="Ananya Rao",
            email="ngo.approved@feedinghope.org",
            role="NGO",
            phone="+91 98765 22001",
            organization_name="Feeding Hope Foundation",
            address="12th Main Road, Indiranagar",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED",
            is_active=True
        )
        ngo_approved.set_password("ngo123")
        db.session.add(ngo_approved)

        ngo_pending = User(
            name="Vikram Sen",
            email="ngo.pending@caremeals.org",
            role="NGO",
            phone="+91 98765 22002",
            organization_name="Care Meals Trust",
            address="ITPL Main Road, Whitefield",
            locality="Whitefield",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="PENDING",
            is_active=True
        )
        ngo_pending.set_password("ngo123")
        db.session.add(ngo_pending)

        ngo3 = User(
            name="Suresh Patel",
            email="ngo@annaseva.org",
            role="NGO",
            phone="+91 98765 22003",
            organization_name="Anna Seva Society",
            address="17th Main, 5th Block, Koramangala",
            locality="Koramangala",
            city="Bengaluru",
            district="Bengaluru Urban",
            verification_status="APPROVED",
            is_active=True
        )
        ngo3.set_password("ngo123")
        db.session.add(ngo3)

        db.session.flush()

        # 4. Food Listings
        now = datetime.utcnow()

        # Listing 1: High Match for Feeding Hope (Indiranagar, Cooked Meals, Urgent in 2.5 hrs)
        listing1 = FoodListing(
            donor_id=donor1.id,
            title="Fresh Lunch Buffet Surplus: Basmati Rice & Paneer Curry",
            category="Cooked Meals",
            description="Freshly prepared vegetarian lunch buffet surplus. Kept under hygienic temperature control in food-grade insulated containers.",
            quantity=45.0,
            unit="Meals",
            food_type="Vegetarian",
            image_filename="listing_1.jpg",
            location="Taj Grand Kitchens, 100 Feet Road",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now - timedelta(hours=1),
            collection_deadline=now + timedelta(hours=2, minutes=30),
            status="AVAILABLE"
        )
        db.session.add(listing1)

        # Listing 2: Bakery Items in Indiranagar (5 hrs)
        listing2 = FoodListing(
            donor_id=donor1.id,
            title="Artisan Sourdough Breads & Morning Pastries",
            category="Bakery Items",
            description="Bakehouse surplus from morning prep. Fresh baguettes, multi-grain sandwich loaves, and assorted buns. Packed in dry food cartons.",
            quantity=35.0,
            unit="Packets",
            food_type="Vegetarian",
            image_filename="listing_2.jpg",
            location="Taj Grand Kitchens, 100 Feet Road",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now - timedelta(hours=2),
            collection_deadline=now + timedelta(hours=5),
            status="AVAILABLE"
        )
        db.session.add(listing2)

        # Listing 3: Critical Urgency in Koramangala (< 1.5 hrs remaining)
        listing3 = FoodListing(
            donor_id=donor2.id,
            title="Warm Canteen Meals: Steamed Rice, Sambar & Mixed Veg Sabzi",
            category="Cooked Meals",
            description="Wholesome dinner canteen preparation ready for immediate evening redistribution to local shelters.",
            quantity=60.0,
            unit="Meals",
            food_type="Vegetarian",
            image_filename="listing_3.jpg",
            location="City College Canteen Block B",
            locality="Koramangala",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now - timedelta(hours=1),
            collection_deadline=now + timedelta(hours=1, minutes=20),
            status="AVAILABLE"
        )
        db.session.add(listing3)

        # Listing 4: Fresh Fruits in Koramangala (18 hrs)
        listing4 = FoodListing(
            donor_id=donor2.id,
            title="Fresh Organic Bananas, Apples & Seasonal Oranges",
            category="Fruits",
            description="Surplus crate of whole seasonal fruit from college dining hall. High nutritional value and safe ambient storage.",
            quantity=25.0,
            unit="kg",
            food_type="Vegetarian",
            image_filename="listing_4.jpg",
            location="City College Canteen Block B",
            locality="Koramangala",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now,
            collection_deadline=now + timedelta(hours=18),
            status="AVAILABLE"
        )
        db.session.add(listing4)

        # Listing 5: Packaged Dairy
        listing5 = FoodListing(
            donor_id=donor1.id,
            title="Chilled Dairy Packets: Fresh Curd & Buttermilk Sachets",
            category="Dairy Products",
            description="Sealed commercial packs, pasteurized, strictly kept in cold storage at 4°C. Perfect for community centers.",
            quantity=30.0,
            unit="Liters",
            food_type="Vegetarian",
            image_filename="listing_5.jpg",
            location="Taj Grand Kitchens, 100 Feet Road",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now - timedelta(hours=1),
            collection_deadline=now + timedelta(hours=7),
            status="AVAILABLE"
        )
        db.session.add(listing5)

        # Listing 6: Active In-Progress Claim (Demonstration of Stepper Step 2 - ACCEPTED)
        listing6 = FoodListing(
            donor_id=donor1.id,
            title="Executive Banquet Chapati & Dal Makhani",
            category="Cooked Meals",
            description="Reserved donation currently progressing through collection workflow.",
            quantity=40.0,
            unit="Meals",
            food_type="Vegetarian",
            image_filename="listing_6.jpg",
            location="Taj Grand Kitchens Banquet Service Bay",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now - timedelta(hours=3),
            collection_deadline=now + timedelta(hours=4),
            status="RESERVED"
        )
        db.session.add(listing6)
        db.session.flush()

        claim6 = Claim(
            listing_id=listing6.id,
            recipient_id=ngo_approved.id,
            status="ACCEPTED",
            notes="Volunteer transport van dispatched; arrival estimated in 45 minutes.",
            created_at=now - timedelta(hours=1, minutes=15),
            updated_at=now - timedelta(minutes=30)
        )
        db.session.add(claim6)

        # Listing 7: Completed Historical Collection (Demonstration of Step 4 - COLLECTED)
        listing7 = FoodListing(
            donor_id=donor2.id,
            title="Freshly Packed Vegetable Pulao & Raita",
            category="Cooked Meals",
            description="Yesterday's successful meal rescue distributed to Shanti Shelter.",
            quantity=50.0,
            unit="Meals",
            food_type="Vegetarian",
            image_filename="listing_7.jpg",
            location="City College Canteen Block B",
            locality="Koramangala",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now - timedelta(days=1, hours=4),
            collection_deadline=now - timedelta(days=1),
            status="COLLECTED",
            created_at=now - timedelta(days=1, hours=5)
        )
        db.session.add(listing7)
        db.session.flush()

        claim7 = Claim(
            listing_id=listing7.id,
            recipient_id=ngo3.id,
            status="COLLECTED",
            notes="Collected on time with insulated thermal boxes.",
            created_at=now - timedelta(days=1, hours=3),
            updated_at=now - timedelta(days=1, hours=1),
            collected_at=now - timedelta(days=1, hours=1)
        )
        db.session.add(claim7)

        # Listing 8: Expired Listing
        listing8 = FoodListing(
            donor_id=donor1.id,
            title="Morning Breakfast Upma & Filter Coffee Prep",
            category="Cooked Meals",
            description="Listing whose collection window elapsed.",
            quantity=15.0,
            unit="Meals",
            food_type="Vegetarian",
            image_filename="listing_8.jpg",
            location="Taj Grand Kitchens",
            locality="Indiranagar",
            city="Bengaluru",
            district="Bengaluru Urban",
            available_from=now - timedelta(hours=12),
            collection_deadline=now - timedelta(hours=2),
            status="EXPIRED",
            created_at=now - timedelta(hours=14)
        )
        db.session.add(listing8)

        # Initial Audit Log
        db.session.add(AuditLog(
            user_id=admin.id,
            action="SYSTEM_INIT",
            entity_type="System",
            details="Database initialized with realistic demo accounts and surplus food listings"
        ))

        db.session.commit()
        print("Database initialized successfully!")


if __name__ == '__main__':
    seed_database()
