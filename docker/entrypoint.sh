#!/bin/bash
set -euo pipefail

PORT="${PORT:-8080}"
APP_ROOT="${APP_ROOT:-/app/backend}"
if [ -z "${MEDIA_ROOT:-}" ]; then
    if [ -d "/data" ]; then
        MEDIA_ROOT="/data/media"
    else
        MEDIA_ROOT="${APP_ROOT}/media"
    fi
fi
RUN_STARTUP_TASKS="${RUN_STARTUP_TASKS:-0}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-${RUN_STARTUP_TASKS}}"
RUN_BOOTSTRAP_AUTH="${RUN_BOOTSTRAP_AUTH:-${RUN_STARTUP_TASKS}}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-0}"
export PORT

echo "[entrypoint] Starting application"
echo "[entrypoint] PORT=${PORT} APP_ROOT=${APP_ROOT} MEDIA_ROOT=${MEDIA_ROOT}"

cd "$APP_ROOT"

# Ensure media directory exists (important when MEDIA_ROOT points to a Railway volume).
mkdir -p "$MEDIA_ROOT"

# Keep a legacy path in sync for deployments that still read media from ${APP_ROOT}/media.
LEGACY_MEDIA_DIR="${APP_ROOT}/media"
if [ "$LEGACY_MEDIA_DIR" != "$MEDIA_ROOT" ]; then
    if [ -d "$LEGACY_MEDIA_DIR" ] && [ ! -L "$LEGACY_MEDIA_DIR" ]; then
        cp -a "$LEGACY_MEDIA_DIR/." "$MEDIA_ROOT/" 2>/dev/null || true
        rm -rf "$LEGACY_MEDIA_DIR" 2>/dev/null || true
    else
        rm -f "$LEGACY_MEDIA_DIR" 2>/dev/null || true
    fi
    ln -s "$MEDIA_ROOT" "$LEGACY_MEDIA_DIR" 2>/dev/null || true
fi

# Optionally seed MEDIA_ROOT with bundled media files on first run.
# Useful when migrating from repo-bundled media to a persistent mounted volume.
INIT_MEDIA_FROM_BUNDLED="${INIT_MEDIA_FROM_BUNDLED:-1}"
BUNDLED_MEDIA_DIR="${APP_ROOT}/media"
if [ "$INIT_MEDIA_FROM_BUNDLED" = "1" ] || [ "$INIT_MEDIA_FROM_BUNDLED" = "true" ] || [ "$INIT_MEDIA_FROM_BUNDLED" = "yes" ]; then
    if [ -d "$BUNDLED_MEDIA_DIR" ] && [ "$BUNDLED_MEDIA_DIR" != "$MEDIA_ROOT" ]; then
        if [ -z "$(ls -A "$MEDIA_ROOT" 2>/dev/null || true)" ]; then
            echo "[entrypoint] Seeding MEDIA_ROOT from bundled media"
            cp -a "$BUNDLED_MEDIA_DIR/." "$MEDIA_ROOT/" 2>/dev/null || true
        fi
    fi
fi

run_with_retries() {
    local description="$1"
    shift
    local attempt=1
    local max_attempts="${STARTUP_RETRIES:-10}"
    local sleep_seconds="${STARTUP_RETRY_SLEEP:-3}"

    until "$@"; do
        if [ "$attempt" -ge "$max_attempts" ]; then
            echo "[entrypoint] ${description} failed after ${attempt} attempts"
            return 1
        fi

        echo "[entrypoint] ${description} failed on attempt ${attempt}/${max_attempts}; retrying in ${sleep_seconds}s"
        attempt=$((attempt + 1))
        sleep "$sleep_seconds"
    done
}

# Esperar a que MySQL esté disponible antes de cualquier operación con la BD
# Usa las mismas variables que settings.py para garantizar consistencia
wait_for_mysql() {
    python3 -c "
import os
import sys
import urllib.parse
import MySQLdb

# Intentar primero con URL (misma prioridad que settings.py)
url = os.environ.get('MYSQL_PRIVATE_URL') or os.environ.get('DATABASE_PRIVATE_URL') or os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL') or os.environ.get('MYSQL_PUBLIC_URL') or ''

try:
    if url and url.startswith(('mysql://', 'mysql2://')):
        parsed = urllib.parse.urlparse(url.replace('mysql2://', 'mysql://'))
        
        # Railway bug workaround: si la URL apunta a internal:3306 pero hay un MYSQL_PORT/MYSQL_HOST público, usarlo
        conn_host = parsed.hostname
        if conn_host == 'mysql.railway.internal' and os.environ.get('MYSQL_HOST') and os.environ.get('MYSQL_HOST') != conn_host:
            conn_host = os.environ.get('MYSQL_HOST')
            
        conn_port = parsed.port or 3306
        if str(conn_port) == '3306' and os.environ.get('MYSQL_PORT') and os.environ.get('MYSQL_PORT') != '3306':
            conn_port = int(os.environ.get('MYSQL_PORT'))

        MySQLdb.connect(
            host=conn_host,
            port=conn_port,
            user=parsed.username,
            passwd=parsed.password or '',
            db=(parsed.path or '').lstrip('/'),
            connect_timeout=5,
        )
    else:
        MySQLdb.connect(
            host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
            port=int(os.environ.get('MYSQL_PORT', 3306)),
            user=os.environ.get('MYSQL_USER', 'root'),
            passwd=os.environ.get('MYSQL_PASSWORD', ''),
            db=os.environ.get('MYSQL_DATABASE') or os.environ.get('MYSQL_NAME', ''),
            connect_timeout=5,
        )
    sys.exit(0)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
"
}
echo "[entrypoint] Esperando conexión a MySQL..."
run_with_retries "mysql-wait" wait_for_mysql
echo "[entrypoint] MySQL disponible"

if [ "$RUN_MIGRATIONS" = "1" ] || [ "$RUN_MIGRATIONS" = "true" ] || [ "$RUN_MIGRATIONS" = "yes" ]; then
    echo "[entrypoint] Running migrations"
    run_with_retries "migrations" python manage.py migrate --noinput
else
    echo "[entrypoint] Skipping migrations (set RUN_MIGRATIONS=1 to enable)"
fi

if [ "$RUN_COLLECTSTATIC" = "1" ] || [ "$RUN_COLLECTSTATIC" = "true" ] || [ "$RUN_COLLECTSTATIC" = "yes" ]; then
    echo "[entrypoint] Collecting static files"
    python manage.py collectstatic --noinput 2>/dev/null || true
else
    echo "[entrypoint] Skipping collectstatic (set RUN_COLLECTSTATIC=1 to enable)"
fi

if [ "$RUN_BOOTSTRAP_AUTH" = "1" ] || [ "$RUN_BOOTSTRAP_AUTH" = "true" ] || [ "$RUN_BOOTSTRAP_AUTH" = "yes" ]; then
echo "[entrypoint] Ensuring auth groups"
run_with_retries "auth group setup" python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()
from django.contrib.auth.models import Group
for name in ['admin', 'user', 'cajero', 'cliente']:
    Group.objects.get_or_create(name=name)
"

echo "[entrypoint] Ensuring default admin"
python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
User = get_user_model()
if User.objects.count() == 0:
    u = os.environ.get('DJANGO_ADMIN_USER', 'admin1')
    p = os.environ.get('DJANGO_ADMIN_PASSWORD', '123456')
    e = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@example.com')
    user = User.objects.create_superuser(u, e, p)
    try:
        user.groups.add(Group.objects.get(name='admin'))
    except Exception:
        pass
    print('Created default admin user:', u)
" 2>/dev/null || true
else
    echo "[entrypoint] Skipping auth bootstrap (set RUN_BOOTSTRAP_AUTH=1 to enable)"
fi

echo "[entrypoint] Iniciando gunicorn en 0.0.0.0:${PORT}"
exec gunicorn django_app.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --log-level info
