"""
Configuración WSGI del proyecto django_app.

Expone la aplicación WSGI como la variable de módulo ``application``.

Para más información sobre este archivo, ver:
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')

application = get_wsgi_application()
