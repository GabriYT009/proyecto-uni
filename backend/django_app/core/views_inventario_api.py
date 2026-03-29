from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Producto
import json

@csrf_exempt
@require_POST
def ajustar_stock_producto(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad'))
        if producto_id is None:
            return JsonResponse({'success': False, 'error': 'ID de producto requerido'}, status=400)
        producto = Producto.objects.get(pk=producto_id)
        if producto.cantidad_disponible is None:
            producto.cantidad_disponible = 0
        producto.cantidad_disponible += cantidad
        producto.save()
        return JsonResponse({'success': True, 'nuevo_stock': producto.cantidad_disponible})
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
