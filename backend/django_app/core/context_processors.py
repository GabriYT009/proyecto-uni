import logging

from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Producto, Nota_Entrega

logger = logging.getLogger(__name__)


def inject_user(request):
    """Make `user` available in all templates, even if auth context processor is disabled."""
    try:
        return {'user': getattr(request, 'user', AnonymousUser())}
    except Exception:
        logger.exception("inject_user fallback: request.user unavailable")
        return {'user': AnonymousUser()}

def contador_carrito(request):
    """
    Este procesador lee la sesión en cada recarga de página 
    y devuelve la cantidad de items en el carrito.
    """
    # Obtenemos el carrito de la sesión, si no existe es una lista vacía.
    # Si la sesión falla (por ejemplo, por BD no disponible), no rompemos el render.
    try:
        cart = request.session.get('cart', [])
    except Exception:
        logger.exception("contador_carrito fallback: session unavailable")
        cart = []
    
    # Devolvemos un diccionario. La clave será el nombre de la 
    # variable que podrás usar en cualquier HTML.
    return {
        'cantidad_carrito_global': len(cart)
    }


def contador_pagos_pendientes(request):
    """
    Devuelve la cantidad de pagos pendientes para admins, para mostrar badge en topbar.
    """
    try:
        user = getattr(request, 'user', AnonymousUser())
        if not getattr(user, 'is_authenticated', False):
            return {'pagos_pendientes_global': 0}

        if not user.groups.filter(name='admin').exists():
            return {'pagos_pendientes_global': 0}

        pendientes = (
            Nota_Entrega.objects
            .filter(comprobante_pago__isnull=False, estado_pago='PENDIENTE')
            .count()
        )
        return {'pagos_pendientes_global': pendientes}
    except Exception:
        logger.exception("contador_pagos_pendientes fallback")
        return {'pagos_pendientes_global': 0}

def add_to_cart(request, producto_id):
    # Verificamos si la petición es POST 
    if request.method == 'POST':
        # 1. Obtenemos el producto de la base de datos para validar que exista

        producto = get_object_or_404(Producto, pk=producto_id, status_producto=True)
        
        # 2. Obtenemos el carrito de la sesión. 
        
        cart = request.session.get('cart', {})
        
        # 3. Convertimos el ID a string (las claves JSON en la sesión deben ser texto)
        prod_id_str = str(producto_id)
        
        # 4. Lógica de sumar 1 o crear el producto en el carrito
        if prod_id_str in cart:
            # Si el producto ya está, le sumamos 1 a la cantidad existente
            cart[prod_id_str]['cantidad'] += 1
        else:
            # Si es la primera vez que se agrega, lo inicializamos en 1
            cart[prod_id_str] = {
                'cantidad': 1,
    
            }
            
        # 5. Guardamos el diccionario actualizado en la sesión
        request.session['cart'] = cart
        request.session.modified = True
        
        # 6. Calculamos la cantidad total de artículos para actualizar el numerito rojo
        # Puedes elegir contar items únicos: len(cart)
        # O sumar todas las cantidades: sum(item['cantidad'] for item in cart.values())
        total_items = sum(item['cantidad'] for item in cart.values())
        
        return JsonResponse({'count': total_items})
        
    # Si alguien intenta entrar por URL directamente (GET), devolvemos un error
    return JsonResponse({'error': 'Método no permitido'}, status=405)