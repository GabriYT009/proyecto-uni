import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()

from core.models import Category

Category.objects.get_or_create(name='Electrónica', slug='electronica')
Category.objects.get_or_create(name='Ropa', slug='ropa')
Category.objects.get_or_create(name='Hogar', slug='hogar')

print('Categorías creadas')