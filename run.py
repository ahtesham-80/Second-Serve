import os
from app import create_app
from app.extensions import db
from seed_data import seed_database

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Ensure database tables exist and seed demo records if new
        db.create_all()
        seed_database()

    print("=" * 65)
    print("   SECOND SERVE: Smart Food Waste Rescue & Redistribution System")
    print("   Application running locally on http://127.0.0.1:5000")
    print("=" * 65)
    print("   Demo Login Accounts:")
    print("   - Admin:          admin@secondserve.org       / admin123")
    print("   - Food Donor:     donor@tajkitchens.com       / donor123")
    print("   - Approved NGO:   ngo.approved@feedinghope.org / ngo123")
    print("   - Pending NGO:    ngo.pending@caremeals.org    / ngo123")
    print("=" * 65)

    app.run(host='127.0.0.1', port=5000, debug=True)
