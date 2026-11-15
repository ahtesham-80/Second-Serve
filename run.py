import os
from app import create_app
from app.extensions import db
from seed_data import seed_database

app = create_app()


def init_app_database(application):
    """
    Ensures database tables and initial seed records exist.
    Executes safely in both local execution and Vercel serverless environments.
    """
    with application.app_context():
        try:
            db.create_all()
            seed_database(app=application)
        except Exception as e:
            application.logger.warning(f"Database auto-initialization skipped or failed: {e}")


# Initialize database tables and seed demo accounts on application startup
init_app_database(app)

if __name__ == '__main__':
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
