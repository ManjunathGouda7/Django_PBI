import os
from .base import *

# Production specific settings
DEBUG = False

# Strict Secret Key enforcement
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("CRITICAL SECURITY ERROR: SECRET_KEY environment variable is required in production!")

# Strict CORS & Domain Origins
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:8000').split(',') if o.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:8000').split(',') if o.strip()]

# Strict Security Headers
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True').lower() in ('true', '1')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Optional PostgreSQL Database via DATABASE_URL if provided
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.config(default=DATABASE_URL, conn_max_age=600)
    except ImportError:
        pass
