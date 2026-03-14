"""
Django settings for django_app project.

Estructura: backend/ (este proyecto) y frontend/ (templates y estáticos) en la raíz del repo.
"""

from pathlib import Path
import os
import dj_database_url

# Cargar variables de entorno desde .env en la raíz del repo (opcional)
def _load_dotenv():
    try:
        from dotenv import load_dotenv
        repo_root = Path(__file__).resolve().parent.parent.parent
        load_dotenv(repo_root / ".env")
    except ImportError:
        pass

_load_dotenv()

# Build paths: BASE_DIR = backend/django_app
BASE_DIR = Path(__file__).resolve().parent
# Raíz del repo (donde están backend/ y frontend/)
REPO_ROOT = BASE_DIR.parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-@%i@jah3u_9f!b*vpzdx(15!xw9c@9187mt%n&4o994j!to=!s")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")

# Allow host from Railway (RAILWAY_PUBLIC_DOMAIN), Render (RENDER_EXTERNAL_HOSTNAME), or env.
# In development, also allow localhost + 127.0.0.1.
def _strip_proto(host: str | None) -> str | None:
    if not host:
        return None
    host = host.strip().replace("https://", "").replace("http://", "")
    return host.rstrip("/")

def _ensure_scheme(origin: str) -> str:
    origin = origin.strip()
    if origin.startswith(("http://", "https://")):
        return origin
    return "https://" + origin.lstrip("/")

railway_host = _strip_proto(os.environ.get("RAILWAY_PUBLIC_DOMAIN"))
render_host = _strip_proto(os.environ.get("RENDER_EXTERNAL_HOSTNAME"))
base_hosts = ["127.0.0.1", "localhost"]
if railway_host:
    base_hosts.append(railway_host)
if render_host:
    base_hosts.append(render_host)

_env_allowed = os.environ.get("ALLOWED_HOSTS", "")
if _env_allowed.strip():
    ALLOWED_HOSTS = [h for h in _env_allowed.split(",") if h]
else:
    ALLOWED_HOSTS = base_hosts

if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = base_hosts

# CSRF trusted origins: Railway, Render, or env.
csrf_trusted = []
if railway_host:
    csrf_trusted.append(f"https://{railway_host}")
if render_host:
    csrf_trusted.append(f"https://{render_host}")

csrf_env = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if csrf_env:
    csrf_trusted += [h.strip() for h in csrf_env.split(",") if h.strip()]

CSRF_TRUSTED_ORIGINS = [_ensure_scheme(h) for h in csrf_trusted if h]


# Application definition

INSTALLED_APPS = [
    # The `homepage` app lives inside the django_app package.
    'django_app.homepage.apps.HomepageConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_app.core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    # WhiteNoise serves static files directly.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# The project is packaged under `django_app`, so URLconf must match.
ROOT_URLCONF = 'django_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(FRONTEND_DIR / "templates")] if FRONTEND_DIR.exists() else [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django_app.core.context_processors.contador_carrito',  # procesador de contexto personalizado
            ],
        },
    },
]

WSGI_APPLICATION = 'django_app.wsgi.application'


# Database
# Prioridad: MYSQL_* o DATABASE_URL (MySQL) -> SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "")
MYSQL_NAME = os.environ.get("MYSQL_DATABASE") or os.environ.get("MYSQL_NAME")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")

if DATABASE_URL.startswith(("mysql://", "mysql2://", "mysql+mysqlconnector://", "mysql+pymysql://")):
    DATABASES = {
        "default": dj_database_url.config(default=DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
elif MYSQL_NAME and MYSQL_USER:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": MYSQL_NAME,
            "USER": MYSQL_USER,
            "PASSWORD": MYSQL_PASSWORD or "",
            "HOST": MYSQL_HOST,
            "PORT": MYSQL_PORT,
            "CONN_MAX_AGE": 600,
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES', default_storage_engine=InnoDB",
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'

# In production (Render, etc) we collect all static files into this folder
# and serve them with WhiteNoise.
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Frontend primero; luego estáticos del backend y temas legacy
_static_dirs = []
if (FRONTEND_DIR / "static").exists():
    _static_dirs.append(str(FRONTEND_DIR / "static"))
_static_dirs.extend([
    str(BASE_DIR / "static"),
    str(BASE_DIR / "extras" / "Presento"),
    str(BASE_DIR / "extras" / "SFI-V2-master"),
])
STATICFILES_DIRS = [d for d in _static_dirs if os.path.exists(d)]

# Use WhiteNoise to serve static files in production (especially when running under Waitress).
# See https://whitenoise.evans.io/en/stable/
STATICFILES_STORAGE = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if not DEBUG else
    'whitenoise.storage.CompressedStaticFilesStorage'
)
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
