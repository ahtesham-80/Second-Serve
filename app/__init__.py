import os
from datetime import datetime

from flask import Flask, render_template, send_from_directory

from app.extensions import db, login_manager
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload and instance directories exist safely (guard against read-only serverless filesystems)
    try:
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'app/static/images/uploads'), exist_ok=True)
    except OSError:
        pass

    try:
        os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.donor import donor_bp
    from app.routes.main import main_bp
    from app.routes.ngo import ngo_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(donor_bp)
    app.register_blueprint(ngo_bp)
    app.register_blueprint(admin_bp)

    # Dedicated route to serve uploaded images (handles both bundled assets and serverless /tmp fallback)
    @app.route('/static/images/uploads/<path:filename>')
    def serve_uploaded_image(filename):
        # 1. Bundled static uploads directory
        bundled_dir = os.path.join(app.root_path, 'static', 'images', 'uploads')
        if os.path.exists(os.path.join(bundled_dir, filename)):
            return send_from_directory(bundled_dir, filename)

        # 2. Serverless /tmp upload fallback
        tmp_dir = os.path.join('/tmp', 'uploads')
        if os.path.exists(os.path.join(tmp_dir, filename)):
            return send_from_directory(tmp_dir, filename)

        # 3. Graceful fallback to default food illustration
        fallback_dir = os.path.join(app.root_path, 'static', 'images', 'food')
        return send_from_directory(fallback_dir, 'buffet_curry.jpg')

    # Context processors for global UI elements
    @app.context_processor
    def inject_global_vars():
        from flask_login import current_user

        from app.models import Claim, FoodListing, User
        
        pending_ngo_badge = 0
        donor_pending_claims = 0
        now = datetime.utcnow()

        if current_user.is_authenticated:
            try:
                if current_user.is_admin:
                    pending_ngo_badge = User.query.filter_by(role='NGO', verification_status='PENDING').count()
                elif current_user.is_donor:
                    donor_pending_claims = Claim.query.join(FoodListing).filter(
                        FoodListing.donor_id == current_user.id,
                        Claim.status == 'PENDING'
                    ).count()
            except Exception:
                pass

        return dict(
            admin_pending_ngos=pending_ngo_badge,
            donor_pending_claims=donor_pending_claims,
            current_utc_now=now
        )

    # Custom Jinja filters
    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%b %d, %Y • %I:%M %p'):
        if not value:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                return value
        return value.strftime(format)

    @app.template_filter('dateonly')
    def dateonly(value, format='%b %d, %Y'):
        if not value:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except Exception:
                return value
        return value.strftime(format)

    # Error handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        try:
            db.session.rollback()
        except Exception:
            pass
        return render_template('errors/500.html'), 500

    return app
