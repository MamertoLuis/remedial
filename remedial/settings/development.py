from .base import *

# Development specific settings
DEBUG = True

# You can override other settings here for development
# For example, using a different database, email backend, etc.
# EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'marty.manguerra@gmail.com'
EMAIL_HOST_PASSWORD = 'sckglyikfghbulqe'
