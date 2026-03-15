#!/bin/bash
set -euo pipefail

PORT="${PORT:-8000}"
APP_ROOT="${APP_ROOT:-/app/backend}"
export PORT

echo "[entrypoint] Starting application"
echo "[entrypoint] PORT=${PORT} APP_ROOT=${APP_ROOT}"

cd "$APP_ROOT"

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

echo "[entrypoint] Running migrations"
run_with_retries "migrations" python manage.py migrate --noinput

echo "[entrypoint] Collecting static files"
python manage.py collectstatic --noinput 2>/dev/null || true

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

echo "[entrypoint] Starting gunicorn on 0.0.0.0:${PORT}"
exec gunicorn django_app.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance
