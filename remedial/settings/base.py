import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# NOTE: BASE_DIR resolves to the inner Django package directory (the parent of
# `remedial/settings`), which is what STATIC_ROOT and the local SQLite database
# currently point at. The repository root (where `manage.py`, `.env` and
# `pyproject.toml` live) is PROJECT_ROOT. Moving BASE_DIR would relocate
# STATIC_ROOT and the local database, so that cleanup is a separate refactor.
PROJECT_ROOT = BASE_DIR.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# In development an insecure fallback is used. Production settings MUST provide
# SECRET_KEY through the environment and fail fast when it is missing
# (see remedial/settings/production.py).
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-only-do-not-use-in-production"
)

# SECURITY WARNING: don't run with debug turned on in production!
# Development settings override this to True.
DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")

# In development, permit local hosts so the admin (e.g. the "Add user" page)
# does not return a 400 Bad Request. Production settings override this through
# the ALLOWED_HOSTS environment variable.
ALLOWED_HOSTS = (["localhost", "127.0.0.1", "[::1]"] if DEBUG else [])


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",  # Custom User model should be prioritized
    "account_master",  # Assuming this is one of the apps in the project
    "compromise_agreement",  # Another app
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "debug_toolbar",
    "django_tables2",
    "crispy_forms",
    "crispy_bootstrap5",
    "django.contrib.humanize",
    "reporting",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "remedial.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates")
        ],  # Assuming a 'templates' directory at project root
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "account_master.context_processors.core_data_edit_allowed",
                "account_master.context_processors.ui_shell",

            ],
        },
    },
]

WSGI_APPLICATION = "remedial.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# Default local database. Production settings replace this with DATABASE_URL.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static"
]  # Assuming a 'static' directory at project root
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Allauth settings
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
AUTH_USER_MODEL = "users.User"

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
