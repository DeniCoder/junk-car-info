import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "postgresql://localhost:5432/junk_car_info")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Настройки интернационализации (i18n)
    BABEL_DEFAULT_LOCALE = os.getenv("BABEL_DEFAULT_LOCALE", "ru")
    LANGUAGES = ['ru', 'en', 'zh', 'es']

    MEDIA_ROOT = os.path.abspath(os.getenv("MEDIA_ROOT", "./media"))
    KEEP_ORIGINAL = os.getenv("KEEP_ORIGINAL", "false").lower() == "true"

    MAX_UPLOAD_FILES = int(os.getenv("MAX_UPLOAD_FILES", "6"))
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "8"))
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

    AUTO_PUBLISH = os.getenv("AUTO_PUBLISH", "false").lower() == "true"

    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

    CLEANUP_ORPHAN_HOURS = int(os.getenv("CLEANUP_ORPHAN_HOURS", "24"))
    CLEANUP_REJECTED_DAYS = int(os.getenv("CLEANUP_REJECTED_DAYS", "7"))
    CLEANUP_PENDING_DAYS = int(os.getenv("CLEANUP_PENDING_DAYS", "30"))

    RATE_LIMIT_STORAGE_URL = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")

    IMAGE_MAX_LONG_EDGE = 1600
    IMAGE_THUMB_SIZE = 320
    IMAGE_WEB_QUALITY = 82
    IMAGE_WEBP_QUALITY = 80

    DEDUP_RADIUS_METERS = 30

    CONTENT_SECURITY_POLICY = {
        "default-src": "'self'",
        "script-src": ["'self'", "'unsafe-inline'", "https://unpkg.com"],
        "style-src": ["'self'", "'unsafe-inline'", "https://unpkg.com", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https://*.tile.openstreetmap.org"],
        "connect-src": ["'self'"],
    }

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 5,
    }
