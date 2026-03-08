"""Package shim so `import django_app` works from repo root.

This makes `django_app` importable even though the real code lives in a
more deeply nested folder (e.g. `pantalla/pantalla/pantalla/django_app`).
"""

import os

# Helper: find the real django_app package directory (contains wsgi.py).
# This makes the shim resilient to different repo layouts (local vs Render).

def _find_real_django_app(root):
    candidates = [
        os.path.join(root, "pantalla", "pantalla", "pantalla", "django_app"),
        os.path.join(root, "pantalla", "pantalla", "django_app"),
        os.path.join(root, "pantalla", "django_app"),
        os.path.join(root, "django_app"),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "wsgi.py")):
            return candidate

    # Fallback: scan for a django_app folder containing wsgi.py.
    for dirpath, dirnames, filenames in os.walk(root):
        if os.path.basename(dirpath) == "django_app" and "wsgi.py" in filenames:
            return dirpath
    return None


# Start from repo root (one level above this shim folder).
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_nested = _find_real_django_app(_repo_root)
if _nested and _nested not in __path__:
    __path__.insert(0, _nested)
