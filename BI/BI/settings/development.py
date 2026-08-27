from .base import *

# Development specific settings
DEBUG = True

# Relax CORS & security settings in development for local testing
CORS_ALLOW_ALL_ORIGINS = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Ensure analytics logger is verbose in dev
LOGGING['loggers']['analytics']['level'] = 'DEBUG'
