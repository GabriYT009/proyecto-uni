from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from .models import Producto


@receiver(post_delete, sender=Producto)
def remove_deleted_product_from_carts(sender, instance, **kwargs):
    """Elimina un producto borrado de todos los carritos en sesión.

    El carrito se guarda en sesión bajo la clave 'cart' como lista de IDs.
    Recorre las sesiones y quita el ID si está presente.
    """
    pid = instance.pk
    if pid is None:
        return

    # Recorrer sesiones y actualizar las que contengan el ID del producto.
    for s in Session.objects.all():
        try:
            store = SessionStore(session_key=s.session_key)
            cart = store.get('cart')
            if cart and pid in cart:
                new_cart = [int(x) for x in cart if int(x) != int(pid)]
                store['cart'] = new_cart
                store.save()
        except Exception:
            # Fallar en silencio para no interrumpir el borrado.
            continue
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore

from .models import Producto


@receiver(post_delete, sender=Producto)
def producto_post_delete(sender, instance, **kwargs):
    """Al borrar un Producto, remover su ID de listas 'cart' en sesión.

    Esto cubre borrados realizados fuera de la vista de eliminación de la app
    (por ejemplo, admin o scripts) para evitar que los carritos apunten
    a productos eliminados.
    """
    prod_id = instance.pk
    if prod_id is None:
        return

    # Recorrer todas las sesiones y quitar el ID del producto de cualquier lista 'cart'.
    for session in Session.objects.all():
        try:
            store = SessionStore(session_key=session.session_key)
            cart = store.get('cart', [])
            if not cart:
                continue
            if prod_id in cart:
                new_cart = [pid for pid in cart if pid != prod_id]
                store['cart'] = new_cart
                store.save()
        except Exception:
            # No permitir que una sesión dañada frene la limpieza.
            continue

