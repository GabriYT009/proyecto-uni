import logging

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Producto

logger = logging.getLogger(__name__)

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