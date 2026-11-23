"""Configuração do Django do Ergo Assist AI."""

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG and os.environ.get("DJANGO_EXIGIR_SECRET", "0") == "1":
        raise RuntimeError("DJANGO_SECRET_KEY ausente em produção (fly secrets set)")
    SECRET_KEY = "dev-inseguro"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# Produção atrás do proxy TLS do Fly.
if os.environ.get("FLY_APP_NAME"):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "catalogo",
    "medidas",
    "conhecimento",
    "assistente",
]

MIDDLEWARE = [
    "config.saude.SaudeMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [],
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

_db = urlparse(os.environ.get("DATABASE_URL", "postgres://ergo:ergo@localhost:5433/ergo"))
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db.path.lstrip("/"),
        "USER": _db.username,
        "PASSWORD": _db.password,
        "HOST": _db.hostname,
        "PORT": _db.port or 5432,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Build do React (frontend/dist) servido na raiz pelo WhiteNoise; o Django
# devolve o index.html para as rotas do SPA (config/urls.py).
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST", BASE_DIR.parent / "frontend" / "dist"))
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_RATES": {
        # O assistente chama LLM: limite por usuário para conter custo e abuso.
        "assistente": os.environ.get("ASSISTENTE_RATE", "30/hour"),
        "anon": "60/hour",
    },
}

# --- IA -------------------------------------------------------------------
OPENROUTER_APIKEY = os.environ.get("OPENROUTER_APIKEY", "")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "")  # fixa UM modelo (testes, comparação)
# Cadeia preferida antes dos grátis, separada por vírgula.
OPENROUTER_MODELS = [m.strip() for m in os.environ.get("OPENROUTER_MODELS", "").split(",") if m.strip()]
# Teto de gasto com LLM por usuário por dia; passou disso, responde no modo sem IA.
LIMITE_GASTO_DIARIO_USD = float(os.environ.get("LIMITE_GASTO_DIARIO_USD", "0.25"))
# Teto somando TODOS os usuários: protege o saldo mesmo com muitas contas.
LIMITE_GASTO_GLOBAL_DIARIO_USD = float(os.environ.get("LIMITE_GASTO_GLOBAL_DIARIO_USD", "1.00"))
# Se definido, o cadastro exige este código (app público sem virar conta aberta).
CODIGO_CONVITE = os.environ.get("CODIGO_CONVITE", "")
EMBEDDINGS = os.environ.get("EMBEDDINGS", "on")
FASTEMBED_CACHE = os.environ.get("FASTEMBED_CACHE", str(BASE_DIR / ".cache" / "fastembed"))
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
DATA_DIR = BASE_DIR / "data"

LOGGING = {
    "version": 1,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "ergo": {"handlers": ["console"], "level": "INFO"},
        "django.request": {"handlers": ["console"], "level": "ERROR"},
    },
}
