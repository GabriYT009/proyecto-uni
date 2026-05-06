from django.apps import AppConfig


class HomepageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # La app está anidada dentro del paquete django_app.
    name = 'django_app.homepage'
