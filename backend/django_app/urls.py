"""
Configuración de URLs del proyecto django_app.

La lista `urlpatterns` enruta URLs hacia las vistas. Para más información:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Ejemplos:
Vistas basadas en funciones
    1. Agrega un import:  from my_app import views
    2. Agrega una URL a urlpatterns:  path('', views.home, name='home')
Vistas basadas en clases
    1. Agrega un import:  from other_app.views import Home
    2. Agrega una URL a urlpatterns:  path('', Home.as_view(), name='home')
Incluir otra configuración de URLs
    1. Importa include(): from django.urls import include, path
    2. Agrega una URL a urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include,path
from django.conf import settings
from django.conf.urls.static import static
from django.urls import re_path
from django.views.static import serve
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
import os

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.png', permanent=False)),
    path('admin/', admin.site.urls),
    # La app `core` vive dentro del paquete django_app.
    path('', include('django_app.core.urls')),
    
]

# Servir archivos media en desarrollo y en despliegues simples
# (por ejemplo, Gunicorn solo en Railway sin Nginx auxiliar).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Fallback para servir media cuando DEBUG=False (deploy simple sin Nginx dedicado).
# Evita 404 en rutas como /media/products/<archivo>.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    # Servir los assets heredados del tema (Presento) directamente en /static/assets/ cuando DEBUG está activo.
    presento_root = os.path.join(settings.BASE_DIR, 'extras', 'Presento', 'assets')
    if os.path.exists(presento_root):
        urlpatterns += [
            re_path(r'^static/assets/(?P<path>.*)$', serve, {'document_root': presento_root}),
        ]

