from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # La app está ubicada dentro del paquete django_app.
    name = 'django_app.core'

    def ready(self):
        # Importar signals para asegurar su registro.
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
