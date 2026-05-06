#!/usr/bin/env python
"""Utilidad de línea de comandos de Django para tareas administrativas."""
import os
import sys


def main():
    # Agregamos backend/ al path para que django_app se resuelva correctamente.
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_app.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Verifica que esté instalado y "
            "disponible en tu PYTHONPATH."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
