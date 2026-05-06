"""
Configuración ASGI del proyecto django_app.

Expone la aplicación ASGI como la variable de módulo ``application``.

Para más información sobre este archivo, ver:
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')

application = get_asgi_application()
