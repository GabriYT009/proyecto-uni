#!/usr/bin/env python
import os
import django
import sys

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from core.models import Categoria, Producto

def delete_electronicos_products():
    try:
        # List all categories and their products
        print("Available categories and product counts:")
        for cat in Categoria.objects.all():
            count = Producto.objects.filter(categoria=cat).count()
            print(f"- {cat.nombre_categoria}: {count} products")
        
        # Find the 'electronicos' category (case insensitive)
        categoria = Categoria.objects.filter(nombre_categoria__iexact='electronicos').first()
        if not categoria:
            # Try with accent
            categoria = Categoria.objects.filter(nombre_categoria__iexact='electrónicos').first()
        if not categoria:
            print("No category named 'electronicos' or 'electrónicos' found.")
            # Perhaps the user means electronic-related categories
            electronic_cats = ['periféricos', 'monitores', 'accesorios']
            total_deleted = 0
            for cat_name in electronic_cats:
                cat = Categoria.objects.filter(nombre_categoria__iexact=cat_name).first()
                if cat:
                    products = Producto.objects.filter(categoria=cat)
                    count = products.count()
                    if count > 0:
                        products.delete()
                        print(f"Deleted {count} products from '{cat.nombre_categoria}' category.")
                        total_deleted += count
            if total_deleted > 0:
                print(f"Total products deleted: {total_deleted}")
            else:
                print("No products to delete in electronic categories.")
            return

        # Get all products in this category
        products = Producto.objects.filter(categoria=categoria)
        count = products.count()
        print(f"Found {count} products in '{categoria.nombre_categoria}' category.")

        if count > 0:
            # Delete the products
            products.delete()
            print(f"Successfully deleted {count} products from '{categoria.nombre_categoria}' category.")
        else:
            print("No products to delete.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    delete_electronicos_products()