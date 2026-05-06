#!/usr/bin/env python
"""Utilidad de línea de comandos de Django para tareas administrativas."""
import os
import sys


def main():
    """Ejecuta tareas administrativas."""

    # Asegura que la raíz del proyecto esté en sys.path para que
    # `import django_app` funcione incluso si se ejecuta desde esta carpeta.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Fuerza el módulo de settings correcto aunque DJANGO_SETTINGS_MODULE
    # ya venga definido en el entorno, por ejemplo desde VS Code.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'django_app.settings'
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Verifica que esté instalado y "
            "disponible en tu variable PYTHONPATH. ¿Olvidaste activar el entorno virtual?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
