"""Entrypoint para Run en Render.

Este archivo ajusta sys.path para que el paquete `django_app` (ubicado en
pantalla/pantalla/pantalla/django_app) sea importable, y luego arranca Waitress.
"""

import os
import sys

# Aseguramos que Python pueda encontrar el paquete django_app.
base = os.path.dirname(os.path.abspath(__file__))
proj = os.path.join(base, "pantalla", "pantalla", "pantalla")
if proj not in sys.path:
    sys.path.insert(0, proj)

from waitress import serve

# Debug: print runtime introspection to logs.
print("cwd:", os.getcwd())
print("sys.path[0..3]:", sys.path[:4])

import django_app
print("django_app.__file__", django_app.__file__)
print("django_app.__path__", list(django_app.__path__))

# Importar después de ajustar sys.path.
from django_app.wsgi import application

# Run migrations on startup so the database schema exists (important for new deployments).
# This is safe for SQLite and avoids "no such table" errors when the DB file is new.
from django.core.management import call_command
try:
    print("Running migrations...")
    call_command("migrate", "--noinput")
except Exception as e:
    # Log but continue; the server can still start even if migrations fail.
    print("Migration error:", e)

port = int(os.environ.get("PORT", 8000))
serve(application, host="0.0.0.0", port=port)
