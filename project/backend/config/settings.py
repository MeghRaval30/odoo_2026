"""
Django settings for PeoplePay360 — HR & Payroll.

Database: SQLite by default so any teammate can clone and run with zero
install friction (D-011). Set DATABASE_URL to point at PostgreSQL and the
Postgres-only constraints in employees/migrations activate automatically.
"""

from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")
if DEBUG:
    # Django's test client sends Host: testserver — needed by smoke_api.py
    ALLOWED_HOSTS += ["testserver"]

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
]

LOCAL_APPS = [
    "core",
    "accounts",
    "employees",
    "attendance",
    "timeoff",
    "payroll",
    "dashboard",
    "intelligence",
    "workforce",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

# Postgres-only features (gist EXCLUDE constraints) are guarded on this flag.
USING_POSTGRES = "postgresql" in DATABASES["default"]["ENGINE"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

#: The real validator list is at the bottom of this file, under Security. This
#: one used to allow six-character passwords, which is not a defensible floor
#: for an account that can move payroll.

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Tokens expire, are re-checked against the network policy on every
        # request, and can be bound to the address they were issued to. See
        # accounts/authentication.py.
        "accounts.authentication.ExpiringTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.StandardPagination",
    "PAGE_SIZE": 50,
}

# --------------------------------------------------------------------------
# Internationalization — India (D-003)
# --------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

CURRENCY_SYMBOL = "₹"
CURRENCY_CODE = "INR"

# --------------------------------------------------------------------------
# Static / media
# --------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# --------------------------------------------------------------------------
# CORS — React dev server
# --------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Only the seven CORS-safelisted response headers are readable from JavaScript
# on a cross-origin response, and the frontend is a different origin from the
# API in development. Content-Disposition is not on that list, so the register
# export's carefully built `filename="register-February-2026.csv"` was invisible
# to the code that reads it and every export landed as the fallback
# "register.csv" -- three months of exports overwriting each other by name.
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

# --------------------------------------------------------------------------
# Email — console backend is sufficient for the demo (PRD-7.5)
# --------------------------------------------------------------------------

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = "payroll@peoplepay360.local"


# --------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------

#: How many reverse proxies sit in front of this app. `X-Forwarded-For` is
#: attacker-controlled, so it is ignored entirely unless this says otherwise —
#: a system that always trusts the header lets anyone claim to be on the office
#: network by setting one. Raise it to the real hop count behind a load
#: balancer, and never higher.
TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "0"))

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Hardening that costs nothing and matters the moment this is not on localhost.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True


# --------------------------------------------------------------------------
# Local language model
# --------------------------------------------------------------------------
#
# The import studio and the natural-language rule compilers talk to a model
# running on this machine through Ollama, never to a hosted API. That is a
# deliberate constraint rather than a cost saving: the data being read is a
# company's salary register, and the argument for letting software touch it at
# all is much easier to make when nothing leaves the host.
#
# It is also optional. Every feature that uses the model has a deterministic
# path behind it, so an evaluator with no GPU still gets a working import --
# the responses say which path ran rather than pretending.
PP360_LLM_ENABLED = os.getenv("PP360_LLM_ENABLED", "1").lower() in ("true", "1", "yes")
PP360_LLM_BASE = os.getenv("PP360_LLM_BASE", "http://127.0.0.1:11434")
PP360_LLM_MODEL = os.getenv("PP360_LLM_MODEL", "qwen2.5:7b")

# A cold load of a 7B model onto an 8GB card costs about eleven seconds; a warm
# generation costs about four. Every request therefore asks Ollama to hold the
# weights resident, and the first request of a session is deliberately paid for
# on a screen that is expecting to wait.
PP360_LLM_KEEP_ALIVE = os.getenv("PP360_LLM_KEEP_ALIVE", "30m")
PP360_LLM_TIMEOUT = int(os.getenv("PP360_LLM_TIMEOUT", "120"))
