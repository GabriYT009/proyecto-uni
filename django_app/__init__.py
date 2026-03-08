"""Package shim so `import django_app` works from repo root.

This makes `django_app` importable even though the real code lives in
`pantalla/pantalla/pantalla/django_app`.
"""

import os

# Ensure the nested django_app folder is on our import path.
# The actual code lives in pantalla/pantalla/pantalla/django_app relative to repo root.
# This file is in <repo>/django_app, so go up one level to reach repo root.
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_nested = os.path.join(_repo_root, "pantalla", "pantalla", "pantalla", "django_app")
if os.path.isdir(_nested) and _nested not in __path__:
    __path__.insert(0, _nested)
