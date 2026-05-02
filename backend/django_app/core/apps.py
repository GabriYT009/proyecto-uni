from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # The app is located under the django_app package.
    name = 'django_app.core'

    def ready(self):
        # import signals to ensure they are registered
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass

        # Register startup checks for external integrations.
        try:
            from . import mailtrap_checks  # noqa: F401
        except Exception:
            pass
