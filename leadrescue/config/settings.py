"""
Django settings for LeadSathi project.

AI-powered Real Estate Lead Management & Analytics platform
built for Indian real estate agencies.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qsl

import environ

# Load env variables
load_dotenv(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))

# ==================================================
# PATH CONFIGURATION
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# ==================================================
# ENVIRONMENT VARIABLES
# ==================================================

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

# Auto-include Render's domain when deployed
_is_render = os.environ.get("RENDER") is not None
_default_hosts = ["localhost", "127.0.0.1"]
if _is_render:
    _default_hosts.append(".onrender.com")

# Read .env file from project root (one level above leadrescue/)
ENV_FILE = BASE_DIR.parent / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(str(ENV_FILE))

# ==================================================
# CORE SETTINGS
# ==================================================

SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS", default=_default_hosts)

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_is_local_host = any(
    host in _LOCAL_HOSTS or host.startswith("127.")
    for host in ALLOWED_HOSTS
)

WSGI_APPLICATION = "config.wsgi.application"

ASGI_APPLICATION = "config.asgi.application"

ROOT_URLCONF = "config.urls"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==================================================
# INSTALLED APPS
# ==================================================

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",
]

THIRD_PARTY_APPS = [
    "django_extensions",
    "sslserver",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "cloudinary_storage",
    "cloudinary",
    "django_celery_beat",
    "django_htmx",
]

LOCAL_APPS = [
    "apps.common",
    "apps.accounts",
    "apps.agencies",
    "apps.leads",
    "apps.dashboard",
    "apps.properties",
    "apps.notifications",
    "apps.reports",
    "apps.core",
    "apps.matching",
    "apps.whatsapp",
    "apps.imports",
    "apps.billing",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==================================================
# MIDDLEWARE
# ==================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.admin_site.AdminOnlyMiddleware",
]

# ==================================================
# TEMPLATES
# ==================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ==================================================
# DATABASE
# ==================================================

db_url = os.getenv("DATABASE_URL", "sqlite:///db.sqlite3")
if db_url.startswith("postgres"):
    tmpPostgres = urlparse(db_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': tmpPostgres.path.replace('/', ''),
            'USER': tmpPostgres.username,
            'PASSWORD': tmpPostgres.password,
            'HOST': tmpPostgres.hostname,
            'PORT': 5432,
            'OPTIONS': dict(parse_qsl(tmpPostgres.query)),
            'DISABLE_SERVER_SIDE_CURSORS': True,
        }
    }
else:
    DATABASES = {
        "default": env.db(
            "DATABASE_URL",
            default="sqlite:///db.sqlite3",
        ),
    }
    if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
        DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# ==================================================
# AUTHENTICATION
# ==================================================

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

# allauth account config (modern syntax for v65+)
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"

# Adapters — custom logic for Agency creation + account linking
ACCOUNT_ADAPTER = "apps.accounts.adapters.CustomAccountAdapter"
SOCIALACCOUNT_ADAPTER = "apps.accounts.adapters.CustomSocialAccountAdapter"

# Skip allauth's intermediate "Continue to Google?" confirmation page
SOCIALACCOUNT_LOGIN_ON_GET = True

# Auto-link Google accounts to existing users with the same verified email
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
        "APPS": [
            {
                "client_id": env("GOOGLE_CLIENT_ID", default=""),
                "secret": env("GOOGLE_CLIENT_SECRET", default=""),
                "key": ""
            }
        ]
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# ==================================================
# RAZORPAY PAYMENT GATEWAY
# ==================================================

RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID", default="")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET", default="")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET", default="")

# ==================================================
# INTERNATIONALIZATION
# ==================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True

# ==================================================
# STATIC FILES
# ==================================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [BASE_DIR / "static"]

STATIC_ROOT = BASE_DIR / "staticfiles"

# Use WhiteNoise manifest storage in production only.
# In development, Django's default static file handling works without collectstatic.
if not DEBUG:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# ==================================================
# MEDIA FILES
# ==================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"

# ==================================================
# CLOUDINARY STORAGE
# ==================================================

CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY", default="")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET", default="")

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
}

USE_CLOUDINARY_IMPORT_STORAGE = env.bool(
    "USE_CLOUDINARY_IMPORT_STORAGE",
    default=_is_render and all([
        CLOUDINARY_CLOUD_NAME,
        CLOUDINARY_API_KEY,
        CLOUDINARY_API_SECRET,
    ]),
)

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    # Merge with existing STORAGES if defined by whitenoise
    if 'STORAGES' not in locals():
        STORAGES = {
            "default": {
                "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            }
        }
    else:
        STORAGES["default"] = {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"
        }

# ==================================================
# CELERY
# ==================================================

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)

CELERY_BROKER_TRANSPORT_OPTIONS = {
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.5,
    'socket_timeout': 3.0,
    'socket_connect_timeout': 3.0,
}

CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)

CELERY_ACCEPT_CONTENT = ["json"]

CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_SERIALIZER = "json"

CELERY_TIMEZONE = TIME_ZONE

CELERY_TASK_TRACK_STARTED = True

CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)

# ==================================================
# WHATSAPP / META APP CONFIG
# ==================================================

WHATSAPP_APP_ID = env("WHATSAPP_APP_ID", default="")
WHATSAPP_APP_SECRET = env("WHATSAPP_APP_SECRET", default="")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = env("WHATSAPP_WEBHOOK_VERIFY_TOKEN", default="")
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default=SECRET_KEY)

# ==================================================
# ADMIN SECURITY
# ==================================================

ADMIN_URL = env("ADMIN_URL", default="harsh-admin/")

# ==================================================
# EMAIL
# ==================================================

EMAIL_PROVIDER = env("EMAIL_PROVIDER", default="console")
RESEND_API_KEY = env("RESEND_API_KEY", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@leadsathi.in")

if EMAIL_PROVIDER == "resend":
    EMAIL_BACKEND = "apps.core.email_backend.ResendEmailBackend"
else:
    EMAIL_BACKEND = env(
        "EMAIL_BACKEND",
        default="django.core.mail.backends.console.EmailBackend",
    )

# ==================================================
# SECURITY (production overrides)
# ==================================================

if not DEBUG and not _is_local_host:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)

# ==================================================
# SESSION SECURITY
# ==================================================

SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days — persistent "remember me" sessions
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # refresh expiry on every request

# ==================================================
# SSL SERVER (local development with HTTPS)
# ==================================================

if DEBUG:
    SSL_CERTIFICATE = BASE_DIR / "adhoc.crt"
    SSL_PRIVATE_KEY = BASE_DIR / "adhoc.key"

    # We run local dev over HTTP (due to pyOpenSSL SSL compatibility issues in Python 3.13),
    # so cookies should NOT be Secure to allow login over HTTP.
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
