import os
import shutil

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def get_database_uri():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        # SQLAlchemy 1.4+ requires 'postgresql://' instead of legacy 'postgres://'
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url

    # Check for Vercel / serverless environment
    is_vercel = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
    if is_vercel:
        tmp_db = os.path.join('/tmp', 'second_serve.db')
        bundled_db = os.path.join(BASE_DIR, 'instance', 'second_serve.db')
        # If pre-seeded DB is bundled and /tmp doesn't have it yet, copy it over
        if os.path.exists(bundled_db) and not os.path.exists(tmp_db):
            try:
                shutil.copyfile(bundled_db, tmp_db)
            except Exception:
                pass
        return f"sqlite:///{tmp_db}"

    # Default local development path
    return f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'second_serve.db')}"


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'second-serve-secure-local-key-2026')
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File uploads: use /tmp in serverless environment to prevent read-only filesystem errors
    IS_SERVERLESS = bool(os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME'))
    if IS_SERVERLESS:
        UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'images', 'uploads')

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost'
