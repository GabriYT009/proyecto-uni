"""Entrypoint para Run en Render.

Este archivo ajusta sys.path para que el paquete `django_app` (ubicado en
pantalla/pantalla/pantalla/django_app) sea importable, y luego arranca Waitress.
"""

import os
import sys

# Aseguramos que Python pueda encontrar el paquete django_app.
base = os.path.dirname(os.path.abspath(__file__))
proj = os.path.join(base, "pantalla", "pantalla")
if proj not in sys.path:
    sys.path.insert(0, proj)

from waitress import serve

# Importar después de ajustar sys.path.
from django_app.wsgi import application

port = int(os.environ.get("PORT", 8000))
serve(application, host="0.0.0.0", port=port)
