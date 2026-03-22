from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from .models import Producto


@receiver(post_delete, sender=Producto)
def remove_deleted_product_from_carts(sender, instance, **kwargs):
    """Remove a deleted product id from all session carts.

    Cart is stored in session under key 'cart' as a list of product IDs.
    This iterates sessions and removes the product id if present.
    """
    pid = instance.pk
    if pid is None:
        return

    # Iterate over sessions and update those that contain the product id
    for s in Session.objects.all():
        try:
            store = SessionStore(session_key=s.session_key)
            cart = store.get('cart')
            if cart and pid in cart:
                new_cart = [int(x) for x in cart if int(x) != int(pid)]
                store['cart'] = new_cart
                store.save()
        except Exception:
            # fail silently to avoid breaking deletion
            continue
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore

from .models import Producto


@receiver(post_delete, sender=Producto)
def producto_post_delete(sender, instance, **kwargs):
    """When a Producto is deleted, remove its id from any session 'cart' lists.

    This handles deletions made outside the application's remove view
    (e.g., admin site or scripts) so users' session carts don't reference
    deleted products.
    """
    prod_id = instance.pk
    if prod_id is None:
        return

    # Iterate all sessions and remove the product id from any 'cart' list
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
            # Don't let one bad session stop the cleanup
            continue
