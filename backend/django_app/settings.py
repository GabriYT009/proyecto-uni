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
DEBUG = True
# os.environ.get("DEBUG", "True").lower() in ("1", "true", "yes")

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

ALLOWED_HOSTS = ["*"]

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


def _is_true(value):
    return str(value or "").strip().lower() in ("1", "true", "yes")


ENABLE_S3_MEDIA = _is_true(os.environ.get("ENABLE_S3_MEDIA", "False"))
_aws_bucket = (os.environ.get("AWS_STORAGE_BUCKET_NAME") or "").strip()
_aws_access_key = (os.environ.get("AWS_ACCESS_KEY_ID") or "").strip()
_aws_secret_key = (os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip()
_aws_region = (
    os.environ.get("AWS_S3_REGION_NAME")
    or os.environ.get("AWS_REGION_NAME")
    or ""
).strip()
_aws_endpoint = (os.environ.get("AWS_S3_ENDPOINT_URL") or "").strip()

# S3-compatible media backend (AWS S3, Cloudflare R2, Backblaze B2, Spaces, etc.).
USE_S3_MEDIA = ENABLE_S3_MEDIA and bool(
    _aws_bucket and _aws_access_key and _aws_secret_key and (_aws_region or _aws_endpoint)
)

if USE_S3_MEDIA:
    INSTALLED_APPS += ['storages']

ENABLE_CLOUDINARY_MEDIA = _is_true(os.environ.get("ENABLE_CLOUDINARY_MEDIA", "False"))

USE_CLOUDINARY_MEDIA = (not USE_S3_MEDIA) and ENABLE_CLOUDINARY_MEDIA and bool(
    os.environ.get("CLOUDINARY_URL")
    or (
        os.environ.get("CLOUDINARY_CLOUD_NAME")
        and os.environ.get("CLOUDINARY_API_KEY")
        and os.environ.get("CLOUDINARY_API_SECRET")
    )
)


def _has_placeholder(value):
    value = (value or "").strip().lower()
    if not value:
        return True
    placeholder_tokens = (
        '<',
        '>',
        'your_',
        'example',
        'changeme',
        'api_key',
        'api_secret',
        'cloud_name',
    )
    return any(token in value for token in placeholder_tokens)


# Avoid crashing uploads when Cloudinary env vars are present but invalid placeholders.
if USE_CLOUDINARY_MEDIA:
    raw_cloudinary_url = os.environ.get("CLOUDINARY_URL", "")
    raw_cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
    raw_api_key = os.environ.get("CLOUDINARY_API_KEY", "")
    raw_api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")

    if _has_placeholder(raw_cloudinary_url) and (
        _has_placeholder(raw_cloud_name)
        or _has_placeholder(raw_api_key)
        or _has_placeholder(raw_api_secret)
    ):
        USE_CLOUDINARY_MEDIA = False

if USE_CLOUDINARY_MEDIA:
    cloudinary_url = os.environ.get("CLOUDINARY_URL")
    if not cloudinary_url and os.environ.get("CLOUDINARY_CLOUD_NAME") and os.environ.get("CLOUDINARY_API_KEY") and os.environ.get("CLOUDINARY_API_SECRET"):
        cloudinary_url = (
            f"cloudinary://{os.environ.get('CLOUDINARY_API_KEY')}:{os.environ.get('CLOUDINARY_API_SECRET')}"
            f"@{os.environ.get('CLOUDINARY_CLOUD_NAME')}"
        )
        os.environ["CLOUDINARY_URL"] = cloudinary_url

    INSTALLED_APPS += [
        'cloudinary',
        'cloudinary_storage',
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
                'django_app.core.context_processors.inject_user',
                'django_app.core.context_processors.contador_carrito',  # procesador de contexto personalizado
            ],
        },
    },
]

if os.environ.get("ENABLE_AUTH_CONTEXT_PROCESSOR", "False").lower() in ("1", "true", "yes"):
    TEMPLATES[0]['OPTIONS']['context_processors'].append('django.contrib.auth.context_processors.auth')

if os.environ.get("ENABLE_MESSAGES_CONTEXT_PROCESSOR", "False").lower() in ("1", "true", "yes"):
    TEMPLATES[0]['OPTIONS']['context_processors'].append('django.contrib.messages.context_processors.messages')

WSGI_APPLICATION = 'django_app.wsgi.application'


# Database
# Prioridad: URL privada de Railway -> DATABASE_URL publica -> MYSQL_* -> SQLite
DATABASE_URL = (
    os.environ.get("MYSQL_PRIVATE_URL")
    or os.environ.get("DATABASE_PRIVATE_URL")
    or os.environ.get("DATABASE_URL")
    or os.environ.get("MYSQL_URL")
    or os.environ.get("MYSQL_PUBLIC_URL")
    or ""
)
MYSQL_NAME = os.environ.get("MYSQL_DATABASE") or os.environ.get("MYSQL_NAME")
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")

DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))
DB_READ_TIMEOUT = int(os.environ.get("DB_READ_TIMEOUT", "10"))
DB_WRITE_TIMEOUT = int(os.environ.get("DB_WRITE_TIMEOUT", "10"))
MYSQL_SSL_REQUIRE = os.environ.get("MYSQL_SSL_REQUIRE", "False").lower() in ("1", "true", "yes")

if DATABASE_URL.startswith(("mysql://", "mysql2://", "mysql+mysqlconnector://", "mysql+pymysql://")):
    # Si DATABASE_URL tiene el puerto de Railway default (3306) pero hay un MYSQL_PORT definido 
    # externamente (ej: 18795), sobrescribir el puerto temporalmente.
    DATABASES = {
        "default": dj_database_url.config(default=DATABASE_URL, conn_max_age=600, ssl_require=MYSQL_SSL_REQUIRE)
    }
    # Forzar puerto y host si las variables explícitas existen y la URL usa el puerto 3306 interno (por bug de Railway)
    if 'PORT' in DATABASES['default'] and DATABASES['default']['PORT'] in ('3306', 3306) and MYSQL_PORT != "3306":
        DATABASES['default']['PORT'] = MYSQL_PORT
    if 'HOST' in DATABASES['default'] and DATABASES['default']['HOST'] == 'mysql.railway.internal' and MYSQL_HOST != 'mysql.railway.internal':
        DATABASES['default']['HOST'] = MYSQL_HOST

    db_options = DATABASES["default"].setdefault("OPTIONS", {})
    db_options.setdefault("connect_timeout", DB_CONNECT_TIMEOUT)
    db_options.setdefault("read_timeout", DB_READ_TIMEOUT)
    db_options.setdefault("write_timeout", DB_WRITE_TIMEOUT)
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
                "connect_timeout": DB_CONNECT_TIMEOUT,
                "read_timeout": DB_READ_TIMEOUT,
                "write_timeout": DB_WRITE_TIMEOUT,
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

MEDIA_URL = os.environ.get("MEDIA_URL", '/media/')
_media_root_env = os.environ.get("MEDIA_ROOT")
_railway_volume_mount = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
if _media_root_env:
    MEDIA_ROOT = Path(_media_root_env)
elif _railway_volume_mount:
    MEDIA_ROOT = Path(_railway_volume_mount) / 'media'
elif Path('/data').exists():
    # Railway volume path (when mounted) without requiring manual env setup.
    MEDIA_ROOT = Path('/data/media')
else:
    MEDIA_ROOT = BASE_DIR / 'media'

if USE_CLOUDINARY_MEDIA:
    # Optional Cloudinary integration: when env vars are present, user-uploaded
    # media is stored remotely instead of Railway ephemeral disk.
    # Support both CLOUDINARY_URL and explicit variables.
    if os.environ.get("CLOUDINARY_CLOUD_NAME"):
        CLOUDINARY_STORAGE = {
            'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
            'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
            'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
            'SECURE': True,
        }

# In production, prefer a single canonical static tree to avoid duplicate paths
# during collectstatic. Local development can opt into the legacy trees.
ENABLE_LEGACY_STATIC_DIRS = os.environ.get("ENABLE_LEGACY_STATIC_DIRS", "False").lower() in ("1", "true", "yes")

_static_dirs = []
if (FRONTEND_DIR / "static").exists():
    _static_dirs.append(str(FRONTEND_DIR / "static"))

if ENABLE_LEGACY_STATIC_DIRS:
    _static_dirs.extend([
        str(BASE_DIR / "static"),
        str(BASE_DIR / "extras" / "Presento"),
        str(BASE_DIR / "extras" / "SFI-V2-master"),
    ])

STATICFILES_DIRS = [d for d in _static_dirs if os.path.exists(d)]

# Use WhiteNoise to serve static files in production (especially when running under Waitress).
# See https://whitenoise.evans.io/en/stable/
USE_MANIFEST_STATICFILES = os.environ.get("USE_MANIFEST_STATICFILES", "False").lower() in ("1", "true", "yes")
_staticfiles_backend = (
    'whitenoise.storage.CompressedManifestStaticFilesStorage'
    if USE_MANIFEST_STATICFILES else
    'whitenoise.storage.CompressedStaticFilesStorage'
)
_default_storage_backend = (
    'storages.backends.s3.S3Storage'
    if USE_S3_MEDIA else
    'cloudinary_storage.storage.MediaCloudinaryStorage'
    if USE_CLOUDINARY_MEDIA else
    'django.core.files.storage.FileSystemStorage'
)
_default_storage_options = {}

if USE_S3_MEDIA:
    _default_storage_options = {
        'access_key': _aws_access_key,
        'secret_key': _aws_secret_key,
        'bucket_name': _aws_bucket,
        'region_name': _aws_region or None,
        'endpoint_url': _aws_endpoint or None,
        'location': (os.environ.get('AWS_MEDIA_LOCATION') or 'media').strip('/'),
        'default_acl': None,
        'file_overwrite': _is_true(os.environ.get('AWS_S3_FILE_OVERWRITE', 'False')),
        'querystring_auth': _is_true(os.environ.get('AWS_QUERYSTRING_AUTH', 'True')),
        'addressing_style': (os.environ.get('AWS_S3_ADDRESSING_STYLE') or 'path'),
        'signature_version': (os.environ.get('AWS_S3_SIGNATURE_VERSION') or 's3v4'),
        'use_ssl': _is_true(os.environ.get('AWS_S3_USE_SSL', 'True')),
    }

    custom_domain = (os.environ.get('AWS_S3_CUSTOM_DOMAIN') or '').strip()
    if custom_domain:
        _default_storage_options['custom_domain'] = custom_domain

    object_params_cache = (os.environ.get('AWS_S3_CACHE_CONTROL') or '').strip()
    if object_params_cache:
        _default_storage_options['object_parameters'] = {
            'CacheControl': object_params_cache,
        }

STORAGES = {
    'default': {
        'BACKEND': _default_storage_backend,
    },
    'staticfiles': {
        'BACKEND': _staticfiles_backend,
    },
}
if _default_storage_options:
    STORAGES['default']['OPTIONS'] = _default_storage_options
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0

# Cookie-backed session/messages avoid hard dependency on DB during template rendering.
SESSION_ENGINE = os.environ.get("SESSION_ENGINE", "django.contrib.sessions.backends.signed_cookies")
MESSAGE_STORAGE = os.environ.get("MESSAGE_STORAGE", "django.contrib.messages.storage.cookie.CookieStorage")

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
