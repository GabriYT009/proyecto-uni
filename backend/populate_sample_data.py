"""Script de utilidad para poblar la base de datos con datos de ejemplo.
Ejecutar desde la raiz del proyecto:

  cd c:\Users\eduar\Desktop\pantalla\backend
  .\..\.venv\Scripts\Activate.ps1
  python populate_sample_data.py

Este script usa el settings actual (DATABASE_URL) y crea objetos si no existen.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django_app.core.models import TipoCliente, Categoria, Producto, Cliente, MetodoPago


def create_sample_data():
    print('Creando Tipos de Cliente...')
    tipo_persona, _ = TipoCliente.objects.get_or_create(tipo_documento='Cédula')
    tipo_empresa, _ = TipoCliente.objects.get_or_create(tipo_documento='RIF')

    print('Creando Categorías...')
    cat_regalos, _ = Categoria.objects.get_or_create(nombre_categoria='Regalería', defaults={
        'descripcion_categoria': 'Productos para regalos',
        'rif_proveedor': 'J-12345678-9',
        'telefono_proveedor': '04141234567',
        'direccion_proveedor': 'Av. Principal, Caracas'
    })
    cat_textil, _ = Categoria.objects.get_or_create(nombre_categoria='Textil', defaults={
        'descripcion_categoria': 'Camisetas, tazas y adornos',
        'rif_proveedor': 'J-98765432-1',
        'telefono_proveedor': '04261234567',
        'direccion_proveedor': 'Calle Secundaria, Barquisimeto'
    })

    print('Creando Productos...')
    productos = [
        {'nombre_producto': 'Camiseta Sublimada', 'descripcion': 'Camiseta de algodón con impresión full color', 'categoria': cat_textil, 'marca_producto': 'TuMarca', 'max_producto': 100, 'precio_venta': 15.5, 'cantidad_disponible': 30},
        {'nombre_producto': 'Taza Sublimada', 'descripcion': 'Taza blanca para foto personalizada', 'categoria': cat_textil, 'marca_producto': 'TuMarca', 'max_producto': 200, 'precio_venta': 9.9, 'cantidad_disponible': 70},
        {'nombre_producto': 'Caja de regalo pequeña', 'descripcion': 'Caja para regalo pequeña', 'categoria': cat_regalos, 'marca_producto': 'RegalosSA', 'max_producto': 50, 'precio_venta': 5.0, 'cantidad_disponible': 40},
    ]

    for p in productos:
        obj, created = Producto.objects.get_or_create(
            nombre_producto=p['nombre_producto'],
            defaults={
                'descripcion': p['descripcion'],
                'categoria': p['categoria'],
                'marca_producto': p['marca_producto'],
                'max_producto': p['max_producto'],
                'precio_venta': p['precio_venta'],
                'cantidad_disponible': p['cantidad_disponible'],
                'status_producto': True,
            }
        )
        if created:
            print('Producto creado:', obj.nombre_producto)

    print('Creando Clientes...')
    clientes = [
        {'documento': 'V12345678', 'nombre_cliente': 'Juan', 'apellido_cliente': 'Pérez', 'direccion': 'Av. Siempre Viva 123', 'telefono_cliente': '04141234567', 'email': 'juan@prueba.com', 'tipo_cliente': tipo_persona},
        {'documento': 'J98765432', 'nombre_cliente': 'Empresa XYZ', 'apellido_cliente': '', 'direccion': 'Calle Falsa 456', 'telefono_cliente': '04141234568', 'email': 'ventas@xyz.com', 'tipo_cliente': tipo_empresa},
    ]

    for c in clientes:
        obj, created = Cliente.objects.get_or_create(
            documento=c['documento'],
            defaults={
                'nombre_cliente': c['nombre_cliente'],
                'apellido_cliente': c['apellido_cliente'],
                'direccion': c['direccion'],
                'telefono_cliente': c['telefono_cliente'],
                'email': c['email'],
                'tipo_cliente': c['tipo_cliente'],
            }
        )
        if created:
            print('Cliente creado:', obj.nombre_cliente)

    print('Creando Métodos de Pago...')
    for nombre in ['Efectivo', 'Transferencia', 'Tarjeta']:
        obj, created = MetodoPago.objects.get_or_create(nombre_metodo_pago=nombre, defaults={'status_pago': True})
        if created:
            print('MetodoPago creado:', obj.nombre_metodo_pago)

    print('Datos de muestra creados satisfactoriamente.')


if __name__ == '__main__':
    create_sample_data()
