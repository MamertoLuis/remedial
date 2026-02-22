from .base import *

# Development specific settings
DEBUG = True

# You can override other settings here for development
# For example, using a different database, email backend, etc.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
