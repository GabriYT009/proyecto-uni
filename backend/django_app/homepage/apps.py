from django.apps import AppConfig


class HomepageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # The app is nested under the django_app package.
    name = 'django_app.homepage'
