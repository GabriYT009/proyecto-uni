import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.django_app.settings')
django.setup()

from core.models import Product, Category

products = Product.objects.all()
print('Productos:')
for p in products:
    print(f'{p.title} - Categoría: {p.category}')

categories = Category.objects.all()
print('Categorías:')
for c in categories:
    print(c.name)