import os

# Auto-select settings module based on DJANGO_ENV environment variable
env = os.getenv('DJANGO_ENV', 'development').lower()

if env in ('production', 'prod'):
    from .production import *
else:
    from .development import *
