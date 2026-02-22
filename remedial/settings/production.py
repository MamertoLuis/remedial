from .base import *

# Production specific settings
DEBUG = False

# Ensure ALLOWED_HOSTS is set in production
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Email backend for production (e.g., SMTP)
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = env.str("EMAIL_HOST", "")
# EMAIL_PORT = env.int("EMAIL_PORT", 587)
# EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", True)
# EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", "")
# EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", "")
