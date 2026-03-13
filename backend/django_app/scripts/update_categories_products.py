#!/usr/bin/env python
import os
import django
import sys

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from core.models import Categoria, Producto

def update_categories_and_products():
    try:
        # Delete existing categories
        Categoria.objects.all().delete()
        print("Deleted existing categories.")

        # Create new categories
        categorias_data = [
            {'nombre_categoria': 'Cajas', 'descripcion_categoria': 'Cajas personalizadas para regalos y eventos'},
            {'nombre_categoria': 'Toppers', 'descripcion_categoria': 'Toppers decorativos para tortas y celebraciones'},
            {'nombre_categoria': 'Sublimación', 'descripcion_categoria': 'Productos con técnica de sublimación'},
            {'nombre_categoria': 'Impresión', 'descripcion_categoria': 'Servicios de impresión personalizada'},
            {'nombre_categoria': 'Personalización', 'descripcion_categoria': 'Artículos personalizados a medida'},
        ]

        categorias = []
        for cat_data in categorias_data:
            cat = Categoria.objects.create(**cat_data)
            categorias.append(cat)
            print(f"Created category: {cat.nombre_categoria}")

        # Create sample products
        productos_data = [
            {'categoria': categorias[0], 'nombre_producto': 'Caja de regalo pequeña', 'descripcion': 'Caja decorada para regalos pequeños', 'precio_venta': 5.00, 'cantidad_disponible': 50},
            {'categoria': categorias[0], 'nombre_producto': 'Caja de regalo mediana', 'descripcion': 'Caja decorada para regalos medianos', 'precio_venta': 8.00, 'cantidad_disponible': 30},
            {'categoria': categorias[0], 'nombre_producto': 'Caja de regalo grande', 'descripcion': 'Caja decorada para regalos grandes', 'precio_venta': 12.00, 'cantidad_disponible': 20},
            {'categoria': categorias[1], 'nombre_producto': 'Topper de cumpleaños', 'descripcion': 'Topper personalizado para tortas de cumpleaños', 'precio_venta': 3.00, 'cantidad_disponible': 100},
            {'categoria': categorias[1], 'nombre_producto': 'Topper de boda', 'descripcion': 'Topper elegante para tortas de boda', 'precio_venta': 5.00, 'cantidad_disponible': 50},
            {'categoria': categorias[1], 'nombre_producto': 'Topper de baby shower', 'descripcion': 'Topper tierno para baby showers', 'precio_venta': 4.00, 'cantidad_disponible': 75},
            {'categoria': categorias[2], 'nombre_producto': 'Taza sublimada', 'descripcion': 'Taza con diseño personalizado por sublimación', 'precio_venta': 10.00, 'cantidad_disponible': 40},
            {'categoria': categorias[2], 'nombre_producto': 'Camiseta sublimada', 'descripcion': 'Camiseta con diseño personalizado', 'precio_venta': 15.00, 'cantidad_disponible': 25},
            {'categoria': categorias[2], 'nombre_producto': 'Taza sublimada con foto', 'descripcion': 'Taza con foto personalizada', 'precio_venta': 12.00, 'cantidad_disponible': 35},
            {'categoria': categorias[3], 'nombre_producto': 'Impresión en papel fotográfico', 'descripcion': 'Impresión de fotos en papel de alta calidad', 'precio_venta': 2.00, 'cantidad_disponible': 200},
            {'categoria': categorias[3], 'nombre_producto': 'Impresión de invitaciones', 'descripcion': 'Invitaciones personalizadas impresas', 'precio_venta': 1.50, 'cantidad_disponible': 150},
            {'categoria': categorias[3], 'nombre_producto': 'Impresión de tarjetas', 'descripcion': 'Tarjetas de visita o felicitación impresas', 'precio_venta': 0.50, 'cantidad_disponible': 300},
            {'categoria': categorias[4], 'nombre_producto': 'Llaveros personalizados', 'descripcion': 'Llaveros con grabado personalizado', 'precio_venta': 4.00, 'cantidad_disponible': 60},
            {'categoria': categorias[4], 'nombre_producto': 'Agenda personalizada', 'descripcion': 'Agenda con diseño a medida', 'precio_venta': 8.00, 'cantidad_disponible': 45},
            {'categoria': categorias[4], 'nombre_producto': 'Cuadernos personalizados', 'descripcion': 'Cuadernos con portada personalizada', 'precio_venta': 6.00, 'cantidad_disponible': 80},
        ]

        for prod_data in productos_data:
            prod = Producto.objects.create(**prod_data)
            print(f"Created product: {prod.nombre_producto} in {prod.categoria.nombre_categoria}")

        print("Successfully updated categories and added sample products.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    update_categories_and_products()