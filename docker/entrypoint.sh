#!/bin/bash
set -e

PORT="${PORT:-8000}"
APP_ROOT="${APP_ROOT:-/app/backend}"
export PORT

cd "$APP_ROOT"

python manage.py migrate --noinput
python manage.py collectstatic --noinput 2>/dev/null || true

python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()
from django.contrib.auth.models import Group
for name in ['admin', 'user', 'cajero', 'cliente']:
    Group.objects.get_or_create(name=name)
"

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

sed "s/__PORT__/${PORT}/g" /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

gunicorn django_app.wsgi:application \
    --bind 127.0.0.1:8002 \
    --workers ${WEB_CONCURRENCY:-2} \
    --threads ${GUNICORN_THREADS:-2} \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance &
GUNICORN_PID=$!

nginx -g 'daemon off;' &
NGINX_PID=$!

trap 'kill -TERM ${GUNICORN_PID} ${NGINX_PID} 2>/dev/null || true; wait ${GUNICORN_PID} ${NGINX_PID} 2>/dev/null || true' TERM INT

wait -n ${GUNICORN_PID} ${NGINX_PID}
EXIT_CODE=$?
kill -TERM ${GUNICORN_PID} ${NGINX_PID} 2>/dev/null || true
wait ${GUNICORN_PID} ${NGINX_PID} 2>/dev/null || true
exit ${EXIT_CODE}
