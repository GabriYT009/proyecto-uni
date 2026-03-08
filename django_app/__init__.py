"""Package shim so `import django_app` works from repo root.

This makes `django_app` importable even though the real code lives in
`pantalla/pantalla/pantalla/django_app`.
"""

import os

# Ensure the nested django_app folder is on our import path.
_here = os.path.dirname(__file__)
_nested = os.path.join(_here, "pantalla", "pantalla", "pantalla", "django_app")
if os.path.isdir(_nested) and _nested not in __path__:
    __path__.insert(0, _nested)
