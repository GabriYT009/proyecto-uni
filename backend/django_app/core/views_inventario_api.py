from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Producto, ProductoTallaStock
import json

@csrf_exempt
@require_POST
def ajustar_stock_producto(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        producto_id = data.get('producto_id')
        cantidad = int(data.get('cantidad') or 0)
        tallas_ajuste = data.get('tallas_ajuste') or {}
        if producto_id is None:
            return JsonResponse({'success': False, 'error': 'ID de producto requerido'}, status=400)

        producto = Producto.objects.get(pk=producto_id)

        if isinstance(tallas_ajuste, dict) and tallas_ajuste:
            existentes = {
                str(s.talla or '').strip().upper(): s
                for s in ProductoTallaStock.objects.filter(producto=producto)
            }

            for talla, delta_raw in tallas_ajuste.items():
                try:
                    delta = int(delta_raw)
                except Exception:
                    continue
                if delta == 0:
                    continue

                talla_key = str(talla or '').strip().upper()
                if not talla_key:
                    continue

                stock_obj = existentes.get(talla_key)
                if stock_obj is None:
                    canonical_talla = 'Unica' if talla_key == 'UNICA' else talla_key
                    stock_obj = ProductoTallaStock.objects.create(
                        producto=producto,
                        talla=canonical_talla,
                        stock_disponible=0,
                    )
                    existentes[talla_key] = stock_obj

                current = int(stock_obj.stock_disponible or 0)
                stock_obj.stock_disponible = max(0, current + delta)
                stock_obj.save(update_fields=['stock_disponible'])

            total = sum(
                int(s.stock_disponible or 0)
                for s in ProductoTallaStock.objects.filter(producto=producto)
            )
            producto.cantidad_disponible = total
            producto.save(update_fields=['cantidad_disponible'])

            tallas_actualizadas = {
                str(s.talla): int(s.stock_disponible or 0)
                for s in ProductoTallaStock.objects.filter(producto=producto)
            }

            return JsonResponse({
                'success': True,
                'nuevo_stock': producto.cantidad_disponible,
                'tallas': tallas_actualizadas,
            })

        if cantidad == 0:
            return JsonResponse({'success': False, 'error': 'No hay ajuste para aplicar'}, status=400)

        current_stock = int(producto.cantidad_disponible or 0)
        producto.cantidad_disponible = max(0, current_stock + cantidad)
        producto.save(update_fields=['cantidad_disponible'])
        return JsonResponse({'success': True, 'nuevo_stock': producto.cantidad_disponible})
    except Producto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
