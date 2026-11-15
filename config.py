import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'second-serve-secure-local-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'second_serve.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'images', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost'
