import logging
from collections import Counter
import importlib
from urllib.parse import urlparse
from django.views import View
from django.template.loader import render_to_string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import user_passes_test, login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User, Group
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.contrib import messages
from django.core.mail import send_mail
from django.core.mail import get_connection
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.db.models import Q, F, Case, When, IntegerField
from django.db.models.functions import Lower, Trim
from django.db.models.deletion import ProtectedError
from django.core.cache import cache
from django.conf import settings
import re
import os
import json
from django.core.exceptions import ObjectDoesNotExist
import requests
from .models import (
    Producto,
    Cliente,
    Categoria,
    Historial_Inventario,
    MetodoPago,
    CarritoDeCompras,
    OrdenDeDespacho,
    SolicitudSublimacion,
    ProductoTallaStock,
    SecurityQuestion,
    UserSecurityAnswer,
    UserCartSnapshot,
)
from django.core.paginator import Paginator
from .forms import ProductForm, PasswordRecoveryForm
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse
from django.core.files.storage import default_storage
import random
import string
import datetime
import unicodedata
import secrets
# Flujo de códigos de restablecimiento de contraseña deshabilitado para verificación de registro
from django.contrib.auth.forms import AuthenticationForm
from .bcv import obtener_tasa_cambio
from .NotaE import Generar_NE
from .image_utils import optimize_uploaded_image

from .models import Producto, Nota_Entrega, CarritoDeCompras, Historial_Inventario, Cliente,Marca_producto


def is_admin(user):
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    return user.groups.filter(name='admin').exists()


def _ensure_default_auth_groups():
    for group_name in ('admin', 'cliente', 'user', 'cajero'):
        Group.objects.get_or_create(name=group_name)


def _normalize_phone_value(phone):
    return re.sub(r'[\s\-()]+', '', (phone or '').strip())


def _validate_phone_value(phone, required=False, field_label='El teléfono'):
    normalized_phone = _normalize_phone_value(phone)
    if not normalized_phone:
        if required:
            return '', f'{field_label} es obligatorio.'
        return '', None

    if not normalized_phone.isdigit():
        return '', f'{field_label} debe contener solo números.'

    if len(normalized_phone) < 10 or len(normalized_phone) > 11:
        return '', f'{field_label} debe tener entre 10 y 11 dígitos.'

    return normalized_phone, None


def _security_questions_ready():
    try:
        tables = set(connection.introspection.table_names())
        return (
            SecurityQuestion._meta.db_table in tables and
            UserSecurityAnswer._meta.db_table in tables
        )
    except Exception:
        return False


def _ensure_default_security_questions():
    if not _security_questions_ready():
        return False

    defaults = [
        '¿Cuál es el nombre de tu primera mascota?',
        '¿En qué ciudad naciste?',
        '¿Cuál es tu comida favorita?',
        '¿Cómo se llama tu mejor amigo de la infancia?',
    ]
    for text in defaults:
        SecurityQuestion.objects.get_or_create(text=text)
    return True


def _ensure_default_admin_user():
    fallback_user = os.environ.get('DJANGO_ADMIN_USER', 'admin1')
    fallback_pass = os.environ.get('DJANGO_ADMIN_PASSWORD', '123456')
    admin_email = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@example.com')

    user_obj, _ = User.objects.get_or_create(
        username=fallback_user,
        defaults={
            'email': admin_email,
            'is_superuser': True,
            'is_staff': True,
        },
    )

    if not user_obj.email:
        user_obj.email = admin_email
    user_obj.is_superuser = True
    user_obj.is_staff = True
    user_obj.set_password(fallback_pass)
    user_obj.save()

    admin_group, _ = Group.objects.get_or_create(name='admin')
    user_obj.groups.add(admin_group)

    return fallback_user, fallback_pass


_CART_SNAPSHOT_CACHE_PREFIX = 'core:cart_snapshot:user:'
_CART_SNAPSHOT_TTL_SECONDS = 60 * 60 * 24 * 30


def _cart_snapshot_cache_key(user_id):
    return f'{_CART_SNAPSHOT_CACHE_PREFIX}{int(user_id)}'


def _normalized_session_cart_payload(request):
    raw_cart = request.session.get('cart', []) or []
    raw_options = request.session.get('cart_options', {}) or {}

    cart = []
    for item in raw_cart:
        try:
            pid = int(item)
        except Exception:
            continue
        if pid > 0:
            cart.append(pid)

    cart_options = {}
    for pid in set(cart):
        option_data = raw_options.get(str(pid))
        if not isinstance(option_data, dict):
            continue
        talla = str(option_data.get('talla') or '').strip()
        if talla:
            cart_options[str(pid)] = {'talla': talla}

    return {
        'cart': cart,
        'cart_options': cart_options,
    }


def _save_cart_snapshot_for_authenticated_user(request):
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return
    try:
        payload = _normalized_session_cart_payload(request)
        cache.set(_cart_snapshot_cache_key(user.pk), payload, _CART_SNAPSHOT_TTL_SECONDS)
        try:
            UserCartSnapshot.objects.update_or_create(
                user=user,
                defaults={
                    'cart': payload.get('cart', []),
                    'cart_options': payload.get('cart_options', {}),
                },
            )
        except Exception:
            logger.exception('No se pudo guardar el respaldo del carrito en BD para user=%s', getattr(user, 'pk', None))
    except Exception:
        logger.exception('No se pudo guardar el respaldo del carrito para user=%s', getattr(user, 'pk', None))


def _restore_cart_snapshot_for_user(request, user):
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    try:
        current_cart = request.session.get('cart', []) or []
        current_options = request.session.get('cart_options', {}) or {}
        if current_cart or current_options:
            return False

        payload = cache.get(_cart_snapshot_cache_key(user.pk)) or {}
        if not isinstance(payload, dict) or (not payload.get('cart') and not payload.get('cart_options')):
            payload = {}
            try:
                db_snapshot = UserCartSnapshot.objects.filter(user=user).values('cart', 'cart_options').first() or {}
                if db_snapshot:
                    payload = {
                        'cart': db_snapshot.get('cart') or [],
                        'cart_options': db_snapshot.get('cart_options') or {},
                    }
                    cache.set(_cart_snapshot_cache_key(user.pk), payload, _CART_SNAPSHOT_TTL_SECONDS)
            except Exception:
                logger.exception('No se pudo leer el respaldo del carrito en BD para user=%s', getattr(user, 'pk', None))

        if not isinstance(payload, dict):
            return False

        saved_cart = payload.get('cart', []) or []
        saved_options = payload.get('cart_options', {}) or {}

        restored_cart = []
        for item in saved_cart:
            try:
                pid = int(item)
            except Exception:
                continue
            if pid > 0:
                restored_cart.append(pid)

        restored_options = {}
        for pid in set(restored_cart):
            opt = saved_options.get(str(pid))
            if not isinstance(opt, dict):
                continue
            talla = str(opt.get('talla') or '').strip()
            if talla:
                restored_options[str(pid)] = {'talla': talla}

        request.session['cart'] = restored_cart
        request.session['cart_options'] = restored_options
        request.session.modified = True
        return bool(restored_cart or restored_options)
    except Exception:
        logger.exception('No se pudo restaurar el respaldo del carrito para user=%s', getattr(user, 'pk', None))
        return False


def _clear_cart_snapshot_for_user(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return
    try:
        cache.delete(_cart_snapshot_cache_key(user.pk))
        try:
            UserCartSnapshot.objects.filter(user=user).delete()
        except Exception:
            logger.exception('No se pudo limpiar el respaldo del carrito en BD para user=%s', getattr(user, 'pk', None))
    except Exception:
        logger.exception('No se pudo limpiar el respaldo del carrito para user=%s', getattr(user, 'pk', None))

def admin_only(view_func):
    decorated_view_func = user_passes_test(is_admin, login_url='login')(login_required(view_func))
    return decorated_view_func

@login_required
@admin_only
def ajustar_inventario_masivo(request):
    productos = (
        Producto.objects
        .select_related('categoria')
        .prefetch_related('stocks_por_talla')
        .order_by('nombre_producto')
    )

    for p in productos:
        p.current_stock = int(p.cantidad_disponible or 0)
        categoria_nombre = (p.categoria.nombre_categoria if p.categoria else '').strip()
        p.is_talla_product = categoria_nombre in ('Camisas', 'Tazas')

        if p.is_talla_product:
            tallas = ['S', 'M', 'L', 'XL', 'XXL'] if categoria_nombre == 'Camisas' else ['Unica']
            stock_map = {
                str(s.talla or '').strip().upper(): int(s.stock_disponible or 0)
                for s in p.stocks_por_talla.all()
            }
            p.tallas_stock = [
                {
                    'name': talla,
                    'stock': stock_map.get(talla.upper(), 0),
                }
                for talla in tallas
            ]
        else:
            p.tallas_stock = []

    return render(request, 'core/ajustar_inventario.html', {'productos': productos})


logger = logging.getLogger(__name__)


def _send_welcome_user_email(user):
    if not user or not getattr(user, 'email', ''):
        return False

    subject = 'Bienvenido a Solucionarte'
    message = (
        f'Hola {user.username},\n\n'
        'Tu usuario fue creado correctamente.\n\n'
        f'Usuario: {user.username}\n'
        'Si no solicitaste este registro, ignora este mensaje.\n'
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
        recipient_list=[user.email],
        fail_silently=False,
    )
    return True


def _send_profile_email_updated_notification(user):
    if not user or not getattr(user, 'email', ''):
        return False

    subject = 'Tu correo fue actualizado'
    message = (
        f'Hola {user.username},\n\n'
        'Te confirmamos que el correo de tu cuenta fue actualizado correctamente.\n\n'
        f'Nuevo correo: {user.email}\n\n'
        'Si no realizaste este cambio, contacta al administrador de inmediato.\n'
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
        recipient_list=[user.email],
        fail_silently=False,
    )
    return True


def _verification_attempts_cache_key(user_id):
    return f'core:email_verification:attempts:{int(user_id)}'


def _generate_verification_code():
    # Flujo de verificación por código deshabilitado. Retorna cadena vacía.
    return ''


def _issue_email_verification_code(user):
    # Deshabilitado: no emitir códigos de verificación.
    return None


def _send_email_verification_code(user, code):
    # Deshabilitado: no enviar códigos de verificación por correo.
    return False

HOME_PRODUCTS_LIMIT = 24
ALLOWED_CATEGORY_NAMES = [
    'Cajas',
    'Toppers',
    'Sublimación',
    'Impresión',
    'Personalización',
    'Papelería',
    'Camisas',
    'Tazas',
]


def _safe_img_url(producto):
    fallback = settings.STATIC_URL + 'assets/img/no-image-placeholder.svg'
    image_field = getattr(producto, 'imagen_producto', None)

    def _build_presigned_url(image_name):
        if not getattr(settings, 'USE_S3_MEDIA', False):
            return ''

        boto3 = None
        try:
            boto3 = importlib.import_module('boto3')
        except Exception:
            return ''

        storage_options = (settings.STORAGES.get('default', {}) or {}).get('OPTIONS', {}) or {}
        access_key = storage_options.get('access_key')
        secret_key = storage_options.get('secret_key')
        endpoint_url = storage_options.get('endpoint_url')
        region_name = storage_options.get('region_name') or 'auto'
        bucket_name = storage_options.get('bucket_name')
        location = (storage_options.get('location') or '').strip('/')
        if not (access_key and secret_key and endpoint_url and bucket_name):
            return ''

        key_name = image_name.lstrip('/')
        if location and not key_name.startswith(location + '/'):
            key_name = f"{location}/{key_name}"

        try:
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                region_name=region_name,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=None,
            )
            return client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key_name},
                ExpiresIn=3600,
            )
        except Exception:
            return ''

    def _normalize_media_url(raw_url):
        if not raw_url:
            return ''
        if raw_url.startswith(('http://', 'https://', '/')):
            return raw_url
        media_base = settings.MEDIA_URL or '/media/'
        if not media_base.endswith('/'):
            media_base += '/'
        return media_base + raw_url.lstrip('/')

    if not image_field:
        return fallback

    image_name = (getattr(image_field, 'name', '') or '').strip()
    if not image_name:
        return fallback

    # Preferir primero la URL directa de FieldFile (URL firmada en buckets privados S3/R2).
    try:
        raw_url = image_field.url
        normalized = _normalize_media_url(raw_url)
        if normalized:
            parsed_url = urlparse(normalized)
            if getattr(settings, 'USE_S3_MEDIA', False) and not parsed_url.query:
                presigned = _build_presigned_url(image_name)
                if presigned:
                    return presigned
            return normalized
    except Exception:
        pass

    # Manejar nombres heredados que ya incluyen la ubicación media (ej. media/products/..)
    # para evitar rutas duplicadas como /media/media/products/.. en backends S3.
    media_location = (os.environ.get('AWS_MEDIA_LOCATION') or 'media').strip('/')
    if media_location and image_name.startswith(media_location + '/'):
        trimmed_name = image_name[len(media_location) + 1:]
        if trimmed_name:
            try:
                alt_url = image_field.storage.url(trimmed_name)
                normalized = _normalize_media_url(alt_url)
                if normalized:
                    return normalized
            except Exception:
                pass

    if getattr(settings, 'USE_S3_MEDIA', False):
        presigned = _build_presigned_url(image_name)
        if presigned:
            return presigned

    try:
        image_basename = os.path.basename(image_name)
        static_fallback_path = os.path.join(settings.FRONTEND_DIR, 'static', 'product-images', image_basename)
        if os.path.exists(static_fallback_path):
            return settings.STATIC_URL + 'product-images/' + image_basename
    except Exception:
        pass

    logger.warning(
        "Image URL fallback to logo | producto_id=%s image_name=%s storage=%s",
        getattr(producto, 'pk', None),
        image_name,
        getattr(getattr(image_field, 'storage', None), '__class__', type(None)).__name__,
    )
    return fallback


def _safe_file_url(file_field):
    if not file_field:
        return ''

    file_name = (getattr(file_field, 'name', '') or '').strip()
    if not file_name:
        return ''

    def _normalize_media_url(raw_url):
        if not raw_url:
            return ''
        if raw_url.startswith(('http://', 'https://', '/')):
            return raw_url
        media_base = settings.MEDIA_URL or '/media/'
        if not media_base.endswith('/'):
            media_base += '/'
        return media_base + raw_url.lstrip('/')

    def _build_presigned_url(file_name):
        if not getattr(settings, 'USE_S3_MEDIA', False):
            return ''

        boto3 = None
        try:
            boto3 = importlib.import_module('boto3')
        except Exception:
            return ''

        storage_options = (settings.STORAGES.get('default', {}) or {}).get('OPTIONS', {}) or {}
        access_key = storage_options.get('access_key')
        secret_key = storage_options.get('secret_key')
        endpoint_url = storage_options.get('endpoint_url')
        region_name = storage_options.get('region_name') or 'auto'
        bucket_name = storage_options.get('bucket_name')
        location = (storage_options.get('location') or '').strip('/')
        if not (access_key and secret_key and endpoint_url and bucket_name):
            return ''

        key_name = file_name.lstrip('/')
        if location and not key_name.startswith(location + '/'):
            key_name = f"{location}/{key_name}"

        try:
            client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                region_name=region_name,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=None,
            )
            return client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': key_name},
                ExpiresIn=3600,
            )
        except Exception:
            return ''

    try:
        normalized = _normalize_media_url(file_field.url)
        if normalized:
            parsed_url = urlparse(normalized)
            if getattr(settings, 'USE_S3_MEDIA', False) and not parsed_url.query:
                presigned = _build_presigned_url(file_name)
                if presigned:
                    return presigned
            return normalized
    except Exception:
        pass

    # Corregir nombres heredados que incluyen media para evitar URLs /media/media/...
    media_location = (os.environ.get('AWS_MEDIA_LOCATION') or 'media').strip('/')
    if media_location and file_name.startswith(media_location + '/'):
        trimmed_name = file_name[len(media_location) + 1:]
        if trimmed_name:
            if getattr(settings, 'USE_S3_MEDIA', False):
                presigned = _build_presigned_url(trimmed_name)
                if presigned:
                    return presigned
            try:
                normalized = _normalize_media_url(file_field.storage.url(trimmed_name))
                if normalized:
                    return normalized
            except Exception:
                pass

    if getattr(settings, 'USE_S3_MEDIA', False):
        presigned = _build_presigned_url(file_name)
        if presigned:
            return presigned

    try:
        normalized = _normalize_media_url(file_field.storage.url(file_name))
        if normalized:
            return normalized
    except Exception:
        pass

    return ''


def _append_to_session_cart(request, product_id):
    cart = request.session.get('cart', []) or []
    cart.append(int(product_id))
    request.session['cart'] = cart
    request.session.modified = True
    _save_cart_snapshot_for_authenticated_user(request)
    return len(cart)


def _set_session_cart_talla(request, product_id, talla):
    cart_options = request.session.get('cart_options', {}) or {}
    product_key = str(int(product_id))
    cart_options[product_key] = {'talla': (talla or '').strip()}
    request.session['cart_options'] = cart_options
    request.session.modified = True
    _save_cart_snapshot_for_authenticated_user(request)


def _get_session_cart_talla(request, product_id):
    cart_options = request.session.get('cart_options', {}) or {}
    return (cart_options.get(str(int(product_id))) or {}).get('talla', '')


def _sublimation_extra_cost(quantity=1):
    try:
        base_cost = float(getattr(settings, 'SUBLIMATION_EXTRA_COST', 0) or 0)
    except Exception:
        base_cost = 0.0

    try:
        qty = max(1, int(quantity or 1))
    except Exception:
        qty = 1

    return round(base_cost * qty, 2)


def _latest_pending_sublimation(user, product_id):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return (
        SolicitudSublimacion.objects
        .filter(usuario=user, producto_id=product_id, carrito_de_compras__isnull=True, estado='PENDIENTE')
        .order_by('-creado_en')
        .first()
    )


def _normalize_talla_label(value):
    text = unicodedata.normalize('NFKD', str(value or '').strip())
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower()


def _sublimation_size_catalog(producto, categoria_nombre):
    tallas_base = ['S', 'M', 'L', 'XL', 'XXL'] if categoria_nombre == 'Camisas' else ['Unica']
    base_by_normalized = {_normalize_talla_label(talla): talla for talla in tallas_base}
    stock_map = {talla: 0 for talla in tallas_base}

    for stock in ProductoTallaStock.objects.filter(producto=producto):
        talla_registrada = str(stock.talla or '').strip()
        talla_canonica = base_by_normalized.get(_normalize_talla_label(talla_registrada))
        if not talla_canonica:
            continue
        stock_map[talla_canonica] += max(0, int(stock.stock_disponible or 0))

    if all(valor <= 0 for valor in stock_map.values()):
        fallback_talla = 'M' if categoria_nombre == 'Camisas' else 'Unica'
        stock_map[fallback_talla] = int(producto.cantidad_disponible or 0)

    tallas = []
    for talla in tallas_base:
        stock = max(0, int(stock_map.get(talla, 0)))
        tallas.append({'talla': talla, 'stock': stock})

    default_talla = next((item['talla'] for item in tallas if item['stock'] > 0), tallas_base[0])
    return tallas, default_talla, {item['talla']: item['stock'] for item in tallas}


def _get_sublimation_stock_record(producto, talla):
    talla_normalizada = (talla or '').strip()
    if not talla_normalizada:
        return None

    direct_match = ProductoTallaStock.objects.filter(producto=producto, talla__iexact=talla_normalizada).first()
    if direct_match:
        return direct_match

    talla_busqueda = _normalize_talla_label(talla_normalizada)
    for stock in ProductoTallaStock.objects.filter(producto=producto):
        if _normalize_talla_label(stock.talla) == talla_busqueda:
            return stock
    return None


def _consume_sublimation_stock(producto, talla, cantidad):
    talla_normalizada = (talla or '').strip()
    if not talla_normalizada:
        return

    stock = _get_sublimation_stock_record(producto, talla_normalizada)
    if stock is None:
        stock = ProductoTallaStock.objects.create(producto=producto, talla=talla_normalizada, stock_disponible=0)

    disponible = int(stock.stock_disponible or 0)
    if cantidad > disponible:
        raise ValueError(f'Stock insuficiente para la talla {talla_normalizada}. Disponible: {disponible}.')

    stock.stock_disponible = disponible - cantidad
    stock.save(update_fields=['stock_disponible'])


def _attach_pending_sublimation(products, user):
    for product in products:
        product.solicitud_sublimacion = _latest_pending_sublimation(user, product.pk)
    return products


def _cached_categories(timeout=300):
    for category_name in ALLOWED_CATEGORY_NAMES:
        Categoria.objects.get_or_create(
            nombre_categoria=category_name,
            defaults={'descripcion_categoria': f'Categoria {category_name}'},
        )
    # Asegurar que 'Otros' exista
    otros_cat, _ = Categoria.objects.get_or_create(
        nombre_categoria='Otros',
        defaults={'descripcion_categoria': 'Productos que no encajan en otras categorías'},
    )

    # Leemos categorias en cada request para reflejar cambios inmediatamente.
    order_case = Case(
        *[When(nombre_categoria=name, then=pos) for pos, name in enumerate(ALLOWED_CATEGORY_NAMES)],
        output_field=IntegerField(),
    )
    categorias = list(
        Categoria.objects
        .filter(nombre_categoria__isnull=False)
        .exclude(nombre_categoria='')
        .exclude(nombre_categoria__startswith='-')
        .filter(nombre_categoria__in=ALLOWED_CATEGORY_NAMES)
        .only('id', 'nombre_categoria')
        .order_by(order_case, 'nombre_categoria')
    )
    # Agregar 'Otros' al final si no está en la lista
    if not any(cat.nombre_categoria == 'Otros' for cat in categorias):
        categorias.append(otros_cat)
    return categorias


def _user_groups(user):
    return list(user.groups.values_list('name', flat=True))

def is_admin(user):
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    return user.groups.filter(name='admin').exists()

def is_regular_user(user):
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    return user.groups.filter(name='user').exists() and not is_admin(user)


def is_cajero(user):
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    return user.groups.filter(name='cajero').exists()

def admin_only(view_func):
    decorated_view_func = user_passes_test(is_admin, login_url='login')(login_required(view_func))
    return decorated_view_func

def cajero_only(view_func):
    decorated_view_func = user_passes_test(is_cajero, login_url='login')(login_required(view_func))
    return decorated_view_func


def shared_access(view_func):
    decorated_view_func = user_passes_test(lambda u: is_admin(u) or is_regular_user(u) or is_cajero(u), login_url='login')(login_required(view_func))
    return decorated_view_func


def login_view(request):
    return render(request, 'core/index.html')

def home(request):
    categories = []
    Productos = []
    Productos_json = '[]'
    cart_count = 0

    # Obtener categorías y productos
    try:
        categories = _cached_categories()
        productos_qs = (
            Producto.objects
            .filter(status_producto=True, cantidad_disponible__gt=0)
            .select_related('categoria')
            .only(
                'id',
                'nombre_producto',
                'precio_venta',
                'descripcion',
                'imagen_producto',
                'categoria__nombre_categoria',
            )
            .order_by('precio_venta')[:HOME_PRODUCTS_LIMIT]
        )
        Productos = list(productos_qs)
        lista_productos_json = []
        for p in Productos:
            img_url = _safe_img_url(p)
            p.img_url = img_url
            lista_productos_json.append({
                'id': p.pk,
                'title': p.nombre_producto,
                'price': p.precio_venta,
                'img': img_url,
                'desc': p.descripcion,
                'Categoria': p.categoria.nombre_categoria if p.categoria else ''
            })
        try:
            Productos_json = json.dumps(lista_productos_json)
        except Exception:
            logger.exception("Failed to serialize Productos_json")
            Productos_json = '[]'
    except Exception:
        logger.exception("Home view fallback: database unavailable or timed out")
        categories = []
        Productos = []
        Productos_json = '[]'

    # Obtener cart_count
    try:
        cart_count = len(request.session.get('cart', []))
    except Exception:
        logger.exception("Home view fallback: session unavailable")
        cart_count = 0

    # Obtener user_groups
    try:
        user_groups = _user_groups(request.user)
    except Exception:
        logger.exception("Home view fallback: unable to read user groups")
        user_groups = []

    # Obtener tasa
    try:
        tasa = obtener_tasa_cambio()
    except Exception:
        tasa = 'N/A'
    try:
        tasa= obtener_tasa_cambio()
    except Exception:
        tasa = 'N/A'

    return render(request, 'core/home.html', {
        'categories': categories, 
        'Productos': Productos, 
        'Productos_json': Productos_json,
        'cart_count': cart_count,
        'user_groups': user_groups,
        'valor_dolar':str(tasa),
    })

def login_post(request):
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = (request.POST.get('password') or '').strip()

        try:
            _ensure_default_auth_groups()
            fallback_user, fallback_pass = _ensure_default_admin_user()

            user = authenticate(request, username=username, password=password)
            if user is not None:
                if not getattr(user, 'is_active', True):
                    return render(request, 'core/index.html', {'error': 'Cuenta no confirmada. Revisa tu correo para activar la cuenta.'})
                login(request, user)
                _restore_cart_snapshot_for_user(request, user)
                return redirect('home')

            # Si la BD aún no tiene usuarios (despliegue nuevo), permitir credenciales admin por defecto.
            if username == fallback_user and password == fallback_pass:
                user_obj, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": os.environ.get("DJANGO_ADMIN_EMAIL", "admin@example.com"),
                        "is_superuser": True,
                        "is_staff": True,
                    },
                )

                user_obj.set_password(password)
                user_obj.is_superuser = True
                user_obj.is_staff = True
                user_obj.save()

                admin_group, _ = Group.objects.get_or_create(name="admin")
                user_obj.groups.add(admin_group)

                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    _restore_cart_snapshot_for_user(request, user)
                    return redirect('home')

            user_exists = User.objects.filter(username=username).exists()
            user_info = None
            if user_exists:
                u = User.objects.filter(username=username).first()
                user_info = {
                    'username': u.username,
                    'is_active': u.is_active,
                    'is_superuser': u.is_superuser,
                    'date_joined': u.date_joined.isoformat() if hasattr(u, 'date_joined') else None,
                }

                if u and not u.is_active:
                    # No usar flujo de verificación por código: informar y pedir soporte
                    return render(request, 'core/index.html', {'error': 'Cuenta inactiva. Contacta al administrador para asistencia.'})

            logger.warning(
                "Login failed. username=%s (repr=%s), user_exists=%s, fallback=%s/%s, info=%s",
                username,
                repr(username),
                user_exists,
                fallback_user,
                "***" if password else "",
                user_info,
            )

            if username and user_exists:
                error = 'Contraseña incorrecta. Verifica tu clave.'
            else:
                error = 'Usuario no encontrado. Verifica tu nombre de usuario.'

            return render(request, 'core/index.html', {'error': error})
        except Exception:
            logger.exception("Login failed due to backend/database error")
            return render(request, 'core/index.html', {
                'error': 'No se pudo iniciar sesion temporalmente. Intenta de nuevo en unos segundos.'
            })
    return redirect('login')


def recuperar_contrasena(request):
    # Flujo en dos pasos: 1) Enviar código por correo, 2) Validar código y actualizar contraseña
    questions = None
    security_feature_enabled = _security_questions_ready()

    def _find_recovery_user(username, email):
        username = (username or '').strip()
        email = (email or '').strip().lower()
        return (
            User.objects
            .annotate(normalized_username=Trim('username'))
            .annotate(normalized_email=Lower(Trim('email')))
            .filter(normalized_username=username, normalized_email=email)
            .first()
        )

    if not security_feature_enabled:
        form = PasswordRecoveryForm(request.POST or None)
        form.add_error(None, 'La recuperación por preguntas de seguridad no está disponible todavía. Intenta más tarde.')
        return render(request, 'core/recuperar_contrasena.html', {
            'form': form,
            'questions': questions,
            'security_feature_enabled': security_feature_enabled,
        })

    if request.method == 'POST':
        form = PasswordRecoveryForm(request.POST)

        # Paso 1: mostrar preguntas de seguridad configuradas para el usuario
        if 'send_code' in request.POST:
            username = (request.POST.get('username') or '').strip()
            email = (request.POST.get('email') or '').strip().lower()

            if not username:
                form.add_error('username', 'El nombre de usuario es obligatorio.')
            if not email:
                form.add_error('email', 'El correo electrónico es obligatorio.')

            if not form.errors:
                user = _find_recovery_user(username, email)
                if user is None:
                    form.add_error(None, 'No encontramos un usuario con esos datos.')
                else:
                    # buscar las respuestas de seguridad para este usuario
                    answers = list(UserSecurityAnswer.objects.filter(user=user).select_related('question'))
                    if not answers:
                        form.add_error(None, 'Este usuario no tiene preguntas de seguridad configuradas. Contacta al administrador.')
                    else:
                        # Elegir aleatoriamente UNA de las respuestas configuradas para mostrar al usuario
                        selected = random.choice(answers)
                        request.session['pr_user_id'] = user.pk
                        request.session['pr_question_id'] = selected.question.pk
                        # Pasamos la única pregunta a la plantilla
                        questions = [selected.question]
                        return render(request, 'core/recuperar_contrasena.html', {'form': form, 'questions': questions})

        # Paso 2: validar respuestas y resetear contraseña
        elif 'reset' in request.POST:
            if form.is_valid():
                new_password = (form.cleaned_data.get('new_password') or '').strip()
                new_password_confirm = (form.cleaned_data.get('new_password_confirm') or '').strip()

                if not new_password:
                    form.add_error('new_password', 'La nueva contraseña es obligatoria.')
                elif len(new_password) < 8:
                    form.add_error('new_password', 'La nueva contraseña debe tener al menos 8 caracteres.')

                if not new_password_confirm:
                    form.add_error('new_password_confirm', 'Debes confirmar la nueva contraseña.')

                if new_password and new_password_confirm and new_password != new_password_confirm:
                    form.add_error('new_password_confirm', 'Las contraseñas no coinciden.')

                if form.errors:
                    return render(request, 'core/recuperar_contrasena.html', {
                        'form': form,
                        'questions': questions,
                        'security_feature_enabled': security_feature_enabled,
                    })

                # Obtener user id desde sesión (establecido en Paso 1)
                user_id = request.session.get('pr_user_id')
                
                user = None
                if user_id:
                    user = User.objects.filter(pk=user_id).first()
                else:
                    # respaldo por username+email
                    username = form.cleaned_data['username'].strip()
                    email = form.cleaned_data['email'].strip().lower()
                    user = _find_recovery_user(username, email)

                if user is None:
                    form.add_error(None, 'No encontramos un usuario con esos datos.')
                else:
                    # Validar únicamente la pregunta seleccionada aleatoriamente en el paso anterior
                    pr_qid = request.session.get('pr_question_id')
                    if not pr_qid:
                        form.add_error(None, 'No se encontró la pregunta a validar. Inicia de nuevo el proceso.')
                    else:
                        ua = UserSecurityAnswer.objects.filter(user=user, question_id=pr_qid).select_related('question').first()
                        if not ua:
                            form.add_error(None, 'No encontramos la pregunta de seguridad para este usuario.')
                        else:
                            posted = (request.POST.get(f'answer_{ua.question.pk}', '') or '').strip()
                            if not ua.check_answer(posted):
                                form.add_error(None, 'La respuesta es incorrecta.')
                            else:
                                user.set_password(new_password)
                                user.save(update_fields=['password'])
                                # limpiar la sesión
                                try:
                                    del request.session['pr_user_id']
                                except Exception:
                                    pass
                                try:
                                    del request.session['pr_question_id']
                                except Exception:
                                    pass
                                if request.user.is_authenticated and request.user.pk == user.pk:
                                    update_session_auth_hash(request, user)
                                messages.success(request, 'Tu contraseña fue actualizada. Ahora puedes iniciar sesión.')
                                return redirect('login')
    else:
        form = PasswordRecoveryForm()

    return render(request, 'core/recuperar_contrasena.html', {
        'form': form,
        'questions': questions,
        'security_feature_enabled': security_feature_enabled,
    })



@login_required
@shared_access
def crear_cliente(request):
    if request.method == 'POST':
        data = request.POST
        form_data = data.dict()
        errors = {}

        tipo = data.get('id_tipo_cliente', '').strip()
        nombre = data.get('nombre_cliente', '').strip()
        apellido = data.get('apellido_cliente', '').strip()
        telefono = data.get('telefono_cliente', '').strip()
        email = data.get('email', '').strip().lower()
        tipo_documento = data.get('tipo_documento', '').strip()
        

        if not tipo:
            errors['id_tipo_cliente'] = 'Seleccione el tipo de cliente.'

        if not nombre:
            errors['nombre_cliente'] = 'El nombre es obligatorio.'
        else:
            if len(nombre) > 45:
                errors['nombre_cliente'] = 'El nombre no puede tener más de 45 caracteres.'
            elif tipo == '2':
                errors['nombre_cliente'] = 'El nombre no puede contener números.'
            elif not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', nombre):
                errors['nombre_cliente'] = 'El nombre contiene caracteres inválidos.'

        # Validar apellido si fue suministrado (no obligatorio)
        if apellido:
            if len(apellido) > 45:
                errors['apellido_cliente'] = 'El apellido no puede tener más de 45 caracteres.'
            elif re.search(r'\d', apellido):
                errors['apellido_cliente'] = 'El apellido no puede contener números.'
            elif not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', apellido):
                errors['apellido_cliente'] = 'El apellido contiene caracteres inválidos.'
                
        telefono, telefono_error = _validate_phone_value(telefono, required=False)
        if telefono_error:
            errors['telefono_cliente'] = telefono_error
            
        if not email:
            errors['email'] = 'El correo electrónico es obligatorio.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = 'El correo electrónico no tiene un formato válido.'

        # Validaciones por tipo de cliente (¡Tal como lo tenías!)
        if tipo == '1':
            cedula = data.get('cedula_dni', '').strip()
            if not cedula:
                errors['cedula_dni'] = 'La cédula es obligatoria para persona natural.'
            elif not cedula.isdigit():
                errors['cedula_dni'] = 'La cédula debe contener solo números.'
            elif len(cedula) > 8:
                errors['cedula_dni'] = 'La cédula no puede tener más de 8 dígitos.'
        elif tipo == '2':
            rif = data.get('rif_empresa', '').strip()
            nombre_empresa = data.get('nombre_empresa', '').strip()
            ced_rep = data.get('cedula_dni_representante', '').strip()
            # Validar RIF: formato letra-prefijo (V,E,J,G) + '-' + dígitos (ej. J-3819192831)
            if not rif:
                errors['rif_empresa'] = 'El RIF es obligatorio para persona jurídica.'
            else:
                # Aceptar formatos como 'J-12345678' o 'j12345678' y normalizar
                rif_norm = rif.upper()
                # permitir formatos con o sin guion: normalizamos a LETRA-DIGITOS
                m = re.match(r'^([VEJG])[-]?(\d{6,20})$', rif_norm, re.IGNORECASE)
                if not m:
                    errors['rif_empresa'] = 'Formato de RIF inválido. Ej: J-3819192831'
                else:
                    # opcional: controlar longitud máxima
                    prefix, digits = m.group(1), m.group(2)
                    if len(digits) > 20:
                        errors['rif_empresa'] = 'El RIF no puede tener más de 20 dígitos.'
                    # si fuera necesario, normalizar en form_data para volver a mostrar
                    form_data['rif_empresa'] = f"{prefix}-{digits}"
            if not nombre_empresa:
                errors['nombre_empresa'] = 'El nombre de la empresa es obligatorio.'
            if not ced_rep:
                errors['cedula_dni_representante'] = 'La cédula del representante es obligatoria.'
            else:
                if not ced_rep.isdigit():
                    errors['cedula_dni_representante'] = 'La cédula del representante debe ser numérica.'
                elif len(ced_rep) > 8:
                    errors['cedula_dni_representante'] = 'La cédula del representante no puede tener más de 8 dígitos.'

        documento_nuevo = ''
        if tipo == '1' and tipo_documento in ('V', 'E'):
            documento_nuevo = f'{tipo_documento}{data.get("cedula_dni", "").strip()}'
        elif tipo == '2':
            # NOTA: Cambié esto para que valide el RIF como ID primario, no la cédula del representante.
            documento_nuevo = form_data.get('rif_empresa', '').strip()

        if documento_nuevo and Cliente.objects.filter(id=documento_nuevo).exists():
            errors['non_field'] = 'El documento o RIF ya está registrado.'

        # Si hay errores, re-renderizar la plantilla con los mensajes y datos previos
        if errors:
            context = {
                'errors': errors,
                'form': form_data,
                'cart_count': len(request.session.get('cart', [])),
                'user_groups': list(request.user.groups.values_list('name', flat=True))
            }
            return render(request, 'core/crear_cliente.html', context)

        # Si todo está bien, crear el registro Cliente en la base de datos
        try:
            # Resolver la FK tipo_cliente (si existe)
            tipo_obj = None
            try:
                from .models import TipoCliente
                tipo_obj = TipoCliente.objects.filter(pk=int(tipo)).first() if tipo else None
            except Exception:
                tipo_obj = None

            cliente_kwargs = {
                'tipo_cliente': tipo_obj,
                'nombre_cliente': nombre,
                'apellido_cliente': apellido,
                'direccion': data.get('direccion','').strip(),
                'telefono_cliente': telefono,
                'email': email,
            }

            # Mapear campos según tipo de cliente a los campos reales del modelo
            if tipo == '1':
                # Persona natural: guardar cédula en `id` (Antes era `documento`)
                if tipo_documento == 'V':
                    cliente_kwargs['id'] = 'V' + data.get('cedula_dni','').strip()
                elif tipo_documento == 'E':
                    cliente_kwargs['id'] = 'E' + data.get('cedula_dni','').strip()
                    
            elif tipo == '2':
                # Persona jurídica: guardar RIF en `id` (Antes era `rif_empresarial`)
                rif_val = form_data.get('rif_empresa', '').strip()
                nombre_emp = data.get('nombre_empresa','').strip()
                if rif_val:
                    cliente_kwargs['id'] = rif_val
                if nombre_emp:
                    cliente_kwargs['nombre_cliente'] = nombre_emp
                    
                # NOTA: La cédula del representante no se asigna al modelo porque ya no 
                # existe la columna `documento` para almacenarla secundariamente.

            cliente = Cliente.objects.create(**cliente_kwargs)
            
        except Exception as ex:
            # Si por alguna razón no se puede guardar, retornar con error genérico y loggable
            errors['non_field'] = 'No fue posible guardar el cliente. Intenta nuevamente.'
            # opcional: adjuntar mensaje más específico en desarrollo
            try:
                errors['debug'] = str(ex)
            except Exception:
                pass
            context = {
                'errors': errors,
                'form': form_data,
                'cart_count': len(request.session.get('cart', [])),
                'user_groups': list(request.user.groups.values_list('name', flat=True))
            }
            return render(request, 'core/crear_cliente.html', context)

        # Guardar temporalmente el email en la sesión y continuar al registro de usuario
        request.session['pending_email'] = email
        return redirect('crear_usuario')

    # GET
    return render(request, 'core/crear_cliente.html', {
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'cart_count': len(request.session.get('cart', []))
    })


def crear_usuario(request):
    security_feature_enabled = False
    security_questions = []

    try:
        security_feature_enabled = _ensure_default_security_questions()
        if security_feature_enabled:
            security_questions = SecurityQuestion.objects.all().order_by('text')
    except (ProgrammingError, OperationalError):
        security_feature_enabled = False
        security_questions = []

    if request.method == 'POST':
        try:
            # 1. Obtener datos del formulario
            username = (request.POST.get('username') or '').strip()
            password = request.POST.get('password')
            password_confirm = request.POST.get('password2') # Corregido nombre variable para claridad
            # security questions: esperamos tres pares (id/custom + answer)
            security_q_ids = [ (request.POST.get(f'security_question_id_{i}') or '').strip() for i in (1,2,3) ]
            security_q_customs = [ (request.POST.get(f'security_question_custom_{i}') or '').strip() for i in (1,2,3) ]
            security_answers = [ (request.POST.get(f'security_answer_{i}') or '').strip() for i in (1,2,3) ]
            
            # Datos para el modelo Cliente
            tipo_documento = (request.POST.get('tipo_documento') or '').strip().upper()
            cedula_dni = (request.POST.get('cedula_dni') or '').strip()
            cedula = f'{tipo_documento}{cedula_dni}'
            nombre = request.POST.get('nombre_cliente')
            apellido = request.POST.get('apellido_cliente')
            direccion = request.POST.get('direccion') # Ojo con el acento en el HTML name='dirección' o 'direccion'
            telefono = request.POST.get('telefono_cliente')
            
            # email 
            email = (request.POST.get('email') or request.session.get('pending_email') or '').strip().lower()

            # -- VALIDACIONES --
            if not username or not password:
                return render(request, 'core/crear_usuario.html', {
                    'error': 'Usuario y contraseña obligatorios.',
                    'security_questions': security_questions,
                    'email': email,
                })
            
            if password != password_confirm:
                return render(request, 'core/crear_usuario.html', {
                    'error': 'Las contraseñas no coinciden.',
                    'security_questions': security_questions,
                    'email': email,
                })

            if security_feature_enabled:
                # validar que las tres preguntas/resp estén presentes
                for idx in (0,1,2):
                    if not security_answers[idx]:
                        return render(request, 'core/crear_usuario.html', {
                            'error': f'La respuesta de seguridad #{idx+1} es obligatoria.',
                            'security_questions': security_questions,
                            'security_feature_enabled': security_feature_enabled,
                            'email': email,
                        })
                    if not security_q_ids[idx] and not security_q_customs[idx]:
                        return render(request, 'core/crear_usuario.html', {
                            'error': f'Selecciona o escribe la pregunta de seguridad #{idx+1}.',
                            'security_questions': security_questions,
                            'security_feature_enabled': security_feature_enabled,
                            'email': email,
                        })
                    if security_q_ids[idx] == 'custom' and not security_q_customs[idx]:
                        return render(request, 'core/crear_usuario.html', {
                            'error': f'Escribe la pregunta personalizada #{idx+1}.',
                            'security_questions': security_questions,
                            'security_feature_enabled': security_feature_enabled,
                            'email': email,
                        })

            if not cedula_dni:
                return render(request, 'core/crear_usuario.html', {
                    'error': 'La cédula es obligatoria.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                })

            if not cedula_dni.isdigit():
                return render(request, 'core/crear_usuario.html', {
                    'error': 'La cédula debe contener solo números.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                })

            if len(cedula_dni) > 8:
                return render(request, 'core/crear_usuario.html', {
                    'error': 'La cédula no puede tener más de 8 dígitos.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                })

            telefono, telefono_error = _validate_phone_value(telefono, required=True)
            if telefono_error:
                return render(request, 'core/crear_usuario.html', {
                    'error': telefono_error,
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                    'telefono': telefono,
                })

            if not email:
                return render(request, 'core/crear_usuario.html', {
                    'error': 'El correo electrónico es obligatorio.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'telefono': telefono,
                })

            try:
                validate_email(email)
            except ValidationError:
                return render(request, 'core/crear_usuario.html', {
                    'error': 'El correo electrónico no tiene un formato válido.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                    'telefono': telefono,
                })

            if User.objects.filter(username=username).exists():
                return render(request, 'core/crear_usuario.html', {
                    'error': 'El usuario ya existe.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                })

            if User.objects.filter(email=email).exists():
                return render(request, 'core/crear_usuario.html', {
                    'error': 'El correo ya está registrado.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                })

            if cedula and Cliente.objects.filter(id=cedula).exists():
                return render(request, 'core/crear_usuario.html', {
                    'error': 'La cédula ya está registrada.',
                    'security_questions': security_questions,
                    'security_feature_enabled': security_feature_enabled,
                    'email': email,
                })

            # CREACIÓN (Usamos atomic para que se creen los dos o ninguno) 
            try:
                with transaction.atomic():
                    # A. Crear el Usuario de Django (activo inmediatamente)
                    nuevo_usuario = User.objects.create_user(
                        username=username,
                        password=password,
                        email=email
                    )
                    nuevo_usuario.is_active = True
                    nuevo_usuario.save(update_fields=['is_active'])

                    # B. Asignar Grupo
                    group, _ = Group.objects.get_or_create(name='cliente')
                    nuevo_usuario.groups.add(group)

                    # C. Crear el Cliente y ENLAZARLO
                    Cliente.objects.create(
                        user=nuevo_usuario,
                        id=cedula,
                        nombre_cliente=nombre,
                        apellido_cliente=apellido,
                        direccion=direccion,
                        telefono_cliente=telefono,
                        email=email
                    )

                    # D. Guardar tres preguntas y respuestas de seguridad (si está habilitado)
                    if security_feature_enabled:
                        # Limpiar respuestas previas si las hay
                        try:
                            UserSecurityAnswer.objects.filter(user=nuevo_usuario).delete()
                        except Exception:
                            logger.exception('No se pudo limpiar UserSecurityAnswer previo para usuario %s', nuevo_usuario.pk)

                        # Recolectar 3 respuestas: fields expected security_question_id_1..3, security_question_custom_1..3, security_answer_1..3
                        for idx in (1, 2, 3):
                            qid = (request.POST.get(f'security_question_id_{idx}') or '').strip()
                            qcustom = (request.POST.get(f'security_question_custom_{idx}') or '').strip()
                            qans = (request.POST.get(f'security_answer_{idx}') or '').strip()

                            if not qans:
                                raise ValueError(f'Respuesta de seguridad #{idx} es obligatoria.')

                            selected_question = None
                            if qid and qid != 'custom':
                                selected_question = SecurityQuestion.objects.filter(pk=qid).first()

                            if selected_question is None and qcustom:
                                selected_question, _ = SecurityQuestion.objects.get_or_create(text=qcustom)

                            if selected_question is None:
                                raise ValueError(f'Pregunta de seguridad #{idx} inválida.')

                            UserSecurityAnswer.objects.create(
                                user=nuevo_usuario,
                                question=selected_question,
                                answer_hash=make_password(qans.lower()),
                            )

                    # Limpieza de sesión
                    if 'pending_email' in request.session:
                        del request.session['pending_email']

                # Registro completado: usuario activo, redirigir a login
                messages.success(request, 'Usuario registrado correctamente. Ya puedes iniciar sesión.')
                return redirect('login')

            except Exception as e:
                # Si algo falla en la base de datos
                raise
        except Exception as e:
            logger.exception('Error en crear_usuario POST')
            error_msg = 'Ocurrió un error al procesar el registro. Intenta de nuevo más tarde.'
            if getattr(settings, 'DEBUG', False):
                error_msg = f'Error al crear usuario: {e}'
            return render(request, 'core/crear_usuario.html', {
                'error': error_msg,
                'security_questions': security_questions,
                'security_feature_enabled': security_feature_enabled,
                'email': (request.POST.get('email') or request.session.get('pending_email') or '').strip().lower(),
            })

    # GET request...

    context = {
        'email': request.session.get('pending_email', ''),
        'security_questions': security_questions,
        'security_feature_enabled': security_feature_enabled,
        'cart_count': len(request.session.get('cart', []))
    }
    return render(request, 'core/crear_usuario.html', context)


def verificar_correo(request):
    # El flujo de verificación por código fue removido. Limpiamos cualquier rastro y redirigimos.
    request.session.pop('pending_verification_user_id', None)
    request.session.pop('pending_verification_email', None)
    request.session.pop('pending_verification_username', None)
    messages.info(request, 'La verificación por código ha sido desactivada. Usa tus credenciales o contacta soporte.')
    return redirect('login')


def confirm_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid).first()
    except Exception:
        user = None

    if user is None:
        messages.error(request, 'Enlace de confirmación inválido o usuario no encontrado.')
        return redirect('login')

    if default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        try:
            _send_welcome_user_email(user)
        except Exception:
            logger.exception('No se pudo enviar correo de bienvenida tras confirmar usuario %s', user.pk)
        messages.success(request, 'Correo confirmado. Ya puedes iniciar sesión.')
        return redirect('login')
    else:
        messages.error(request, 'El enlace de confirmación es inválido o expiró.')
        return redirect('login')

@login_required
@admin_only

def crear_Productoo(request):
    marcas = []
    try:
        marcas= Marca_producto.objects.all()
        if request.method == 'POST':
            post_data = request.POST.copy()
            categoria_seleccion = post_data.get('categoria')
            otra_categoria = post_data.get('otra_categoria')

            # Si seleccionó 'otros', usar la categoría 'Otros' existente o crearla.
            if categoria_seleccion == 'otros':
                otros_cat, _ = Categoria.objects.get_or_create(
                    nombre_categoria='Otros',
                    defaults={'descripcion_categoria': 'Productos que no encajan en otras categorías'},
                )
                post_data['categoria'] = otros_cat.pk
            elif categoria_seleccion and categoria_seleccion != 'otros':
                post_data['categoria'] = categoria_seleccion
            # Si no seleccionó nada, dejarlo vacío
            form = ProductForm(post_data, request.FILES)
            if form.is_valid():
                producto = form.save()
                messages.success(request, f'Producto "{producto.nombre_producto}" creado exitosamente.')
                return redirect('inventario')
            else:
                messages.error(request, 'Por favor corrige los errores en el formulario.')
        else:
            form = ProductForm()
            
    except Exception as e:
        import traceback
        print('Error en crear_Productoo:', e)
        traceback.print_exc()
        messages.error(request, f'Error al crear producto: {e}')
        form = ProductForm(request.POST or None, request.FILES or None)

    return render(request, 'core/crear_productoo.html', {
        'form': form,
        'marcas': marcas,
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'cart_count': len(request.session.get('cart', []))
    })


def crear_Productoo_debug(request):
    """Modo debug para reproducir /producto/registrar sin la verificación completa de grupos."""
    error = None
    form = None
    try:
        if request.method == 'POST':
            form = ProductForm(request.POST, request.FILES)
            if form.is_valid():
                producto = form.save()
                messages.success(request, f'Producto "{producto.nombre_producto}" creado exitosamente (debug).')
                return redirect('inventario')
        else:
            form = ProductForm()
    except Exception as e:
        import traceback
        error = traceback.format_exc()
        print('crear_Productoo_debug error:', error)
        messages.error(request, f'Error al crear producto: {e}')
        form = form or ProductForm(request.POST or None, request.FILES or None)

    return render(request, 'core/crear_Productoo.html', {
        'form': form,
        'user_groups': [],
        'cart_count': len(request.session.get('cart', [])),
        'debug_error': error,
    })


def catalog(request):
    # Obtenemos el parámetro de la URL (ej: ?Categoria=Electronica)
    categoria_param = request.GET.get('Categoria')
    search_param = request.GET.get('search', '').strip()
    # product_id_param fue removido: usar `search` para la navegación del catálogo
    
    # Variable para guardar el objeto categoría encontrado (si existe)
    categoria_obj = None

    # Base queryset: incluimos todos los productos para que también se vean
    # los inactivos o sin stock en el catálogo, pero el carrito los bloquea.
    Productos = (
        Producto.objects
        .select_related('categoria')
        .only(
            'id',
            'nombre_producto',
            'precio_venta',
            'descripcion',
            'imagen_producto',
            'cantidad_disponible',
            'categoria__nombre_categoria',
            'categoria_id',
        )
    )

    if categoria_param:
        categoria_normalizada = (categoria_param or '').strip().lower()

        # Al entrar a la categoría "Sublimación" mostramos también
        # categorías sublimables como Camisas y Tazas.
        if categoria_normalizada in ('sublimacion', 'sublimación'):
            Productos = Productos.filter(
                categoria__nombre_categoria__in=['Sublimación', 'Camisas', 'Tazas']
            )
            categoria_obj = Categoria.objects.filter(nombre_categoria__iexact='Sublimación').first()
        else:
            try:
                # Usamos __iexact para que 'ropa' encuentre 'Ropa' (insensible a mayúsculas).
                categoria_obj = Categoria.objects.get(nombre_categoria__iexact=categoria_param)

                # Filtramos productos por categoría
                Productos = Productos.filter(categoria=categoria_obj)

            except Categoria.DoesNotExist:
                # Si escriben una categoría que no existe, mostramos todos los productos activos
                pass
    
    if search_param:
        # Filtramos por nombre del producto o descripción (insensible a mayúsculas)
        Productos = Productos.filter(
            Q(nombre_producto__icontains=search_param) |
            Q(descripcion__icontains=search_param)
        )

    # NOTA: se prefiere búsqueda del lado servidor con `search`.
    # El enrutamiento exacto por product_id se removió para mantener consistencia con Enter.

    categories = _cached_categories()

    # Paginación: mostrar 10 productos por página
    per_page = 10
    paginator = Paginator(Productos.order_by('nombre_producto'), per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Construir JSON solo con los productos de la página actual (más eficiente)
    lista_productos_json = []
    for p in page_obj.object_list:
        img_url = _safe_img_url(p)
        p.img_url = img_url
        p.has_stock = (p.cantidad_disponible or 0) > 0
        lista_productos_json.append({
            'id': p.pk,
            'title': p.nombre_producto,
            'price': p.precio_venta,
            'img': img_url,
            'desc': p.descripcion,
            'Categoria': p.categoria.nombre_categoria if p.categoria else ''
        })
    Productos_json = json.dumps(lista_productos_json, ensure_ascii=False)

    try:
        tasa= obtener_tasa_cambio()
    except Exception:
        tasa = 'N/A'

    return render(request, 'core/catalog.html', {
        'Productos': page_obj, 
        'categories': categories, 
        'selected_Categoria': categoria_obj.nombre_categoria if categoria_obj else categoria_param,
        'search_query': search_param,
        'search_has_unavailable': any((p.cantidad_disponible or 0) <= 0 for p in page_obj.object_list) if search_param else False,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user),
        'Productos_json': Productos_json,
        'page_obj': page_obj,
        'paginator': paginator,
        'valor_dolar':str(tasa),
    })


@login_required
def perfil(request):
    # Vista sencilla de perfil: muestra información básica del usuario si está autenticado
    user = request.user if request.user.is_authenticated else None

    # Intentar localizar un registro Cliente asociado al email del usuario
    cliente = None
    cedula = ''
    telefono = ''
    nombre = ''
    apellido = ''
    direccion = ''
    try:
        if user and user.email:
            cliente = Cliente.objects.filter(email__iexact=user.email).first()
            if cliente:
                # soportar diferentes nombres de campo según la versión del modelo
                cedula = getattr(cliente, 'documento', '') or ''
                telefono = getattr(cliente, 'telefono_cliente', None) or getattr(cliente, 'telefono', '') or ''
                nombre = getattr(cliente, 'nombre_cliente', '') or ''
                apellido = getattr(cliente, 'apellido_cliente', '') or ''
                direccion = getattr(cliente, 'direccion', '') or ''
    except Exception:
        cliente = None

    if request.method == 'POST' and user and user.is_authenticated:
        nombre = (request.POST.get('nombre_cliente') or '').strip()
        apellido = (request.POST.get('apellido_cliente') or '').strip()
        direccion = (request.POST.get('direccion') or '').strip()
        telefono = (request.POST.get('telefono_cliente') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        previous_email = (user.email or '').strip().lower()
        normalized_email = email.lower()
        email_changed = bool(normalized_email) and normalized_email != previous_email

        telefono, telefono_error = _validate_phone_value(telefono, required=False)
        if telefono_error:
            messages.error(request, telefono_error)
            return redirect('perfil')

        if email:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, 'El correo electrónico no tiene un formato válido.')
                return redirect('perfil')

        if not cliente and user.email:
            cliente = Cliente.objects.filter(email__iexact=user.email).first()

        try:
            with transaction.atomic():
                if cliente is None:
                    cliente = Cliente(user=user)

                cliente.nombre_cliente = nombre
                cliente.apellido_cliente = apellido
                cliente.direccion = direccion
                cliente.telefono_cliente = telefono
                if email:
                    cliente.email = email
                    user.email = email

                cliente.save()
                if email:
                    user.save(update_fields=['email'])

                if email_changed:
                    try:
                        _send_profile_email_updated_notification(user)
                    except Exception:
                        logger.exception('No se pudo enviar el correo de confirmación de cambio de email al usuario %s', user.pk)

                messages.success(request, 'Información del cliente actualizada correctamente.')
                return redirect('perfil')
        except Exception as e:
            messages.error(request, f'No se pudo actualizar el perfil: {e}')

    return render(request, 'core/perfil.html', {
        'user': user,
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'cart_count': len(request.session.get('cart', [])),
        'cliente': cliente,
        'cedula': cedula,
        'telefono': telefono,
        'nombre': nombre,
        'apellido': apellido,
        'direccion': direccion,
    })


@login_required

def carrito(request):
    raw_cart = request.session.get('cart', []) or []
    cart = []
    for item in raw_cart:
        try:
            cart.append(int(item))
        except (TypeError, ValueError):
            continue

    unique_ids = set(cart)
    productos_qs = (
        Producto.objects
        .filter(pk__in=unique_ids, status_producto=True)
        .only('id', 'nombre_producto', 'precio_venta', 'descripcion', 'imagen_producto', 'cantidad_disponible')
    )
    productos_map = {p.pk: p for p in productos_qs}

    carrito_validado = [pid for pid in cart if pid in productos_map]
    if carrito_validado != raw_cart:
        request.session['cart'] = carrito_validado
        request.session.modified = True

    cantidades = Counter(carrito_validado)
    Productos = list(productos_map.values())
    _attach_pending_sublimation(Productos, request.user)
    for p in Productos:
        p.cantidad_en_carrito = cantidades.get(p.pk, 0)
        p.talla = _get_session_cart_talla(request, p.pk)
        p.img_url = _safe_img_url(p)
        if (p.cantidad_disponible or 0) <= 0:
            p.status_producto = False
    
    # Si se solicita comprar directamente desde el carrito (GET ?buy=ID), obtener el producto
    buy_id = request.GET.get('buy')
    producto_compra = None
    if buy_id:
        try:
            buy_id_int = int(buy_id)
            producto_compra = productos_map.get(buy_id_int)
            if producto_compra is None:
                producto_compra = Producto.objects.filter(pk=buy_id_int, status_producto=True).first()
        
            if producto_compra:
                producto_compra.img_url = _safe_img_url(producto_compra)
        except Exception:
            producto_compra = None

    show_purchase_only = bool(producto_compra)
    total_bs = ''
    try:
        tasa= obtener_tasa_cambio()
        total_carrito = 0.0
        for p in Productos:
            cantidad = getattr(p, 'cantidad_en_carrito', 0) or 0
            subtotal = float(p.precio_venta or 0) * cantidad
            costo_sublimacion = _sublimation_extra_cost(cantidad) if getattr(p, 'solicitud_sublimacion', None) else 0.0
            total_carrito += subtotal + costo_sublimacion
        total_bs= total_carrito * float(tasa) if tasa != 'N/A' else 'N/A'
        total_bs = f"{total_bs:.2f}"
    except Exception:
        tasa = 'N/A'
    
    return render(request, 'core/carrito.html', {
        'Productos': Productos,
        'producto_compra': producto_compra,
        'show_purchase_only': show_purchase_only,
        'cart_count': len(carrito_validado),
        'user_groups': _user_groups(request.user),
        'valor_dolar':str(tasa),
        'total_bs': total_bs,
        'sublimation_extra_cost': _sublimation_extra_cost(),
        
    })





#NOTA: Las funciones add_to_cart y remove_from_cart manejan el carrito de compras en la sesión del usuario.
#DE MOMENTO NO AGREGANDO NI ELIMINANDO PRODUCTOS DEL CARRITO EN LA BASE DE DATOS.

def add_to_cart(request, product_id):
    try:
        product_id_int = int(product_id)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Producto inválido.'}, status=400)

    producto = Producto.objects.filter(pk=product_id_int).only('id', 'status_producto', 'cantidad_disponible').first()
    if not producto:
        return JsonResponse({'success': False, 'error': 'Producto no encontrado.'}, status=404)
    if not producto.status_producto:
        return JsonResponse({'success': False, 'error': 'Este producto está inactivo y no se puede agregar al carrito.'}, status=400)
    if (producto.cantidad_disponible or 0) <= 0:
        return JsonResponse({'success': False, 'error': 'Este producto no tiene stock disponible.'}, status=400)

    cart = request.session.get('cart', [])

    cart.append(product_id)
    request.session['cart'] = cart
    request.session.modified = True
    _save_cart_snapshot_for_authenticated_user(request)

    return JsonResponse({'success': True, 'count': len(cart)})

@login_required
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', [])
    cart_options = request.session.get('cart_options', {}) or {}

    # Eliminar el producto por completo del carrito en sesión, aunque aparezca varias veces.
    pid = str(product_id)
    cart = [item for item in cart if str(item) != pid]
    cart_options.pop(pid, None)
    request.session['cart'] = cart
    request.session['cart_options'] = cart_options
    request.session.modified = True
    _save_cart_snapshot_for_authenticated_user(request)
    return redirect('carrito')


def logout_view(request):
    """Cerrar sesión del usuario actual y redirigir al login."""
    try:
        _save_cart_snapshot_for_authenticated_user(request)
        logout(request)
    except Exception:
        pass
    return redirect('login')


@login_required
@shared_access
def caja(request):
    # Mostrar interfaz de caja: cliente + factura a la izquierda, lista de productos a la derecha
    productos = (
        Producto.objects
        .filter(status_producto=True)
        .only('id', 'nombre_producto', 'precio_venta', 'cantidad_disponible', 'imagen_producto')
        .order_by('nombre_producto')[:120]
    )
    # preparar imagen urls
    for p in productos:
        p.img_url = _safe_img_url(p)

    # cargar clientes para autocompletar cedula
    from .models import Cliente
    clientes = list(
        Cliente.objects
        .exclude(id__isnull=True)
        .exclude(id__exact='')
        .values('id', 'nombre_cliente', 'apellido_cliente', 'direccion', 'telefono_cliente')
    )


    try:
        tasa= obtener_tasa_cambio()
    except Exception:
        tasa = 'N/A'

    return render(request, 'core/caja.html', {
        'productos': productos,
        'clientes': clientes,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user),
        'valor_dolar':str(tasa),
    })

@login_required
@shared_access
def cobrar_caja(request):
    """Procesa cobro desde Caja usando Nota_Entrega y CarritoDeCompras como detalle."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Metodo no permitido'}, status=405)
    
    tasa = obtener_tasa_cambio()
    valor_bcv = float(tasa) if tasa != 'N/A' else 0.00

    # 1. Primero decodificamos el JSON
    try:
        payload = json.loads(request.body or '{}')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Payload JSON invalido'}, status=400)

    # 2. AHORA SÍ sacamos la cédula y los items del payload decodificado
    cliente_doc = payload.get('cliente_doc', '').strip()
    cliente_nombre = payload.get('cliente_nombre', '').strip()
    cliente_direccion = payload.get('cliente_direccion', '').strip()
    cliente_telefono = payload.get('cliente_telefono', '').strip()
    raw_items = payload.get('items') or []
    
    if not isinstance(raw_items, list) or not raw_items:
        return JsonResponse({'success': False, 'error': 'No hay productos para cobrar'}, status=400)

    # Agrupar cantidades por producto
    qty_by_product = {}
    for item in raw_items:
        try:
            pid = int(item.get('id'))
            qty = int(item.get('qty', 1))
        except Exception:
            continue
        if pid <= 0 or qty <= 0:
            continue
        qty_by_product[pid] = qty_by_product.get(pid, 0) + qty

    if not qty_by_product:
        return JsonResponse({'success': False, 'error': 'No hay productos validos para cobrar'}, status=400)

    # Cargar productos y validar existencia
    productos = {
        p.pk: p for p in Producto.objects.filter(pk__in=qty_by_product.keys(), status_producto=True)
    }

    for pid in qty_by_product.keys():
        if pid not in productos:
            return JsonResponse({'success': False, 'error': f'Producto no disponible (ID {pid})'}, status=400)

    try:
        with transaction.atomic():
            # PASO A: Buscar el cliente de forma ESTRICTA (no con contains)
            cliente_datos = None
            if cliente_doc:
                # Usamos documento=cliente_doc para buscar coincidencia exacta
                cliente_datos = Cliente.objects.filter(id=cliente_doc).first() 

            # Crear la Nota de Entrega
            nota_kwargs = {
                'cliente': cliente_datos,
                'estado_pago': 'APROBADO',
                'fecha': timezone.now(),
                'total': 0.0,
                'bcv': valor_bcv,
                'fecha_revision': timezone.now(),
                'revisado_por_id': request.user.pk,
            }

            # Para clientes no registrados, guardamos un snapshot de datos digitados en Caja.
            if not cliente_datos:
                nota_kwargs['cliente_documento'] = cliente_doc[:45] if cliente_doc else ''
                nota_kwargs['cliente_nombre'] = cliente_nombre[:90] if cliente_nombre else 'Consumidor Final'
                nota_kwargs['cliente_direccion'] = cliente_direccion[:100] if cliente_direccion else ''
                nota_kwargs['cliente_telefono'] = cliente_telefono[:15] if cliente_telefono else ''

            nota = Nota_Entrega.objects.create(
                **nota_kwargs,
            )

            total_acumulado = 0.0

            # PASO B: Procesar cada producto y crear sus detalles
            for pid, cantidad in qty_by_product.items():
                producto = productos[pid]
                disponible = producto.cantidad_disponible or 0

                if cantidad > disponible:
                    raise ValueError(f'Stock insuficiente para "{producto.nombre_producto}". Disponible: {disponible}.')

                subtotal_item = float(producto.precio_venta or 0) * cantidad
                
                # Crear el detalle vinculado a la Nota_Entrega
                CarritoDeCompras.objects.create(
                    Nota_Entrega=nota,
                    Producto=producto,
                    Cantidad=cantidad,
                    precio_unitario=producto.precio_venta,
                    status_carrito=True
                )

                # PASO C: Actualizar inventario e historial
                cantidad_anterior = producto.cantidad_disponible or 0
                producto.cantidad_disponible = max(0, cantidad_anterior - cantidad)
                producto.save(update_fields=['cantidad_disponible'])

                Historial_Inventario.objects.create(
                    producto=producto,
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=producto.cantidad_disponible,
                    tipo_movimiento='venta',
                    motivo=f'Cobro en caja (Nota #{nota.id})',
                    usuario_responsable=request.user.username,
                )

                total_acumulado += subtotal_item

            # PASO D: Actualizar el total final de la nota
            nota.total_bruto = total_acumulado
            nota.total = total_acumulado
            nota.save()

        messages.success(request, 'Venta en caja procesada exitosamente.')
        return JsonResponse({
            'success': True,
            'nota_id': nota.id,
            'message': 'Pago procesado exitosamente.',
            'redirect_url': reverse('caja'),
        })

    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f"Error interno: {str(e)}"}, status=500)

@login_required
def descargar_factura_ne(request, pk):
    nota = get_object_or_404(Nota_Entrega, pk=pk)
    pdf = Generar_NE(nota) # Instanciamos tu clase
    return pdf.generate_invoice() # Llamamos al método que retorna la HttpResponse

@login_required
@admin_only
def inventario(request):
    debug_media = request.GET.get('debug_media', '').strip().lower() in ('1', 'true', 'yes')
    productos = (
        Producto.objects
        .select_related('categoria', 'marca_producto')
        .only(
            'id',
            'nombre_producto',
            'descripcion',
            'precio_venta',
            'cantidad_disponible',
            'status_producto',
            'categoria_id',
            'categoria__nombre_categoria',
            'marca_producto_id',
            'marca_producto__nombre_marca',
            'imagen_producto',
        )
        .order_by('nombre_producto')
    )

    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '').strip()
    brand = request.GET.get('brand', '').strip()
    status = request.GET.get('status', '').strip().lower()

    if search:
        productos = productos.filter(nombre_producto__icontains=search)
    if category and category.lower() != 'all':
        productos = productos.filter(categoria__nombre_categoria__iexact=category)
    if brand and brand.lower() != 'all':
        productos = productos.filter(marca_producto__nombre_marca__iexact=brand)
    if status == 'activo':
        productos = productos.filter(status_producto=True)
    elif status == 'inactivo':
        productos = productos.filter(status_producto=False)

    # Paginación: 10 productos por página
    paginator = Paginator(productos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for p in page_obj.object_list:
        p.img_url = _safe_img_url(p)
        p.stock_disponible = (p.cantidad_disponible or 0) > 0

    # Añadir motivo de la última reducción (si existe) a cada producto de la página
    try:
        page_product_ids = [p.pk for p in page_obj.object_list]
        motivos_map = {}
        if page_product_ids:
            rows = (
                Historial_Inventario.objects
                .filter(producto_id__in=page_product_ids, cantidad_nueva__lt=F('cantidad_anterior'))
                .order_by('producto_id', '-fecha_ajuste')
                .values('producto_id', 'motivo')
            )
            for row in rows:
                pid = row['producto_id']
                if pid not in motivos_map:
                    motivos_map[pid] = row['motivo']

        for p in page_obj.object_list:
            p.ultimo_motivo_resto = motivos_map.get(p.pk, '')
    except Exception:
        # No bloquear la vista si hay algún problema con historial
        for p in page_obj.object_list:
            p.ultimo_motivo_resto = ''

    return render(request, 'core/inventario.html', {
        'productos': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'categories': _cached_categories(),
        'brands': Marca_producto.objects.order_by('nombre_marca'),
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user),
        'debug_media': debug_media,
        'search': search,
        'category': category,
        'brand': brand,
        'status': status,
    })

@login_required
@admin_only

def producto_detalle(request, producto_id):
    try:
        producto = Producto.objects.get(pk=producto_id)

        # Reutilizar la misma logica segura de imagen usada en catalogo/home.
        producto.img_url = _safe_img_url(producto)
        
        from_inventario = request.GET.get('origin') == 'inventario'
        return render(request, 'core/producto_detalle.html', {
            'producto': producto,
            'cart_count': len(request.session.get('cart', [])),
            'from_inventario': from_inventario,
            'user_groups': list(request.user.groups.values_list('name', flat=True))
        })
    except Producto.DoesNotExist:
        return render(request, 'core/404.html', status=404)


@login_required
def camisas_shein(request, producto_id):
    producto = get_object_or_404(
        Producto.objects.select_related('categoria'),
        pk=producto_id,
        status_producto=True,
        cantidad_disponible__gt=0,
    )
    categoria_nombre = (producto.categoria.nombre_categoria if producto.categoria else '').strip()
    if categoria_nombre not in ('Camisas', 'Tazas'):
        return redirect('comprar_producto', producto_id=producto.pk)

    producto.img_url = _safe_img_url(producto)
    tallas, default_talla, stock_por_talla = _sublimation_size_catalog(producto, categoria_nombre)
    es_taza = categoria_nombre == 'Tazas'

    if es_taza:
        default_talla = 'Unica'

    if request.method == 'POST':
        accion = (request.POST.get('accion') or '').strip().lower()
        talla_raw = (request.POST.get('talla') or default_talla).strip()
        talla_key_map = {_normalize_talla_label(key): key for key in stock_por_talla.keys()}
        talla = talla_key_map.get(_normalize_talla_label(talla_raw), talla_raw)
        if es_taza:
            talla = 'Unica'
        try:
            cantidad = int(request.POST.get('cantidad', '1') or 1)
        except ValueError:
            cantidad = 1

        stock_seleccionado = int(stock_por_talla.get(talla, 0))

        if cantidad <= 0:
            messages.error(request, 'Debes seleccionar una cantidad válida.')
            return redirect('camisas_shein', producto_id=producto.pk)

        if talla and talla not in stock_por_talla:
            messages.error(request, 'La talla seleccionada no es válida.')
            return redirect('camisas_shein', producto_id=producto.pk)

        if cantidad > stock_seleccionado:
            messages.error(request, f'No hay suficiente stock para la talla {talla}. Disponible: {stock_seleccionado}.')
            return redirect('camisas_shein', producto_id=producto.pk)

        if accion == 'agregar_carrito':
            _set_session_cart_talla(request, producto.pk, talla)
            for _ in range(cantidad):
                _append_to_session_cart(request, producto.pk)
            messages.success(request, 'Camisa agregada al carrito.')
            return redirect('carrito')

        if accion == 'guardar_sublimacion':
            comentario = (request.POST.get('comentario') or '').strip()
            imagen = request.FILES.get('imagen_sublimacion')
            costo_sublimacion = _sublimation_extra_cost(cantidad)

            if talla and talla not in stock_por_talla:
                messages.error(request, 'La talla seleccionada no es válida.')
                return redirect('camisas_shein', producto_id=producto.pk)

            if not imagen:
                messages.error(request, 'Debes subir una imagen para la sublimación.')
                return redirect('camisas_shein', producto_id=producto.pk)

            imagen = optimize_uploaded_image(imagen, max_size=(1400, 1400), quality=80)

            SolicitudSublimacion.objects.create(
                usuario=request.user,
                producto=producto,
                talla=talla,
                cantidad=cantidad,
                comentario=comentario,
                imagen_sublimacion=imagen,
                estado='PENDIENTE',
            )
            _set_session_cart_talla(request, producto.pk, talla)
            for _ in range(cantidad):
                _append_to_session_cart(request, producto.pk)
            if costo_sublimacion > 0:
                messages.success(request, f'Sublimación guardada. Recargo adicional: $ {costo_sublimacion:.2f}. Producto agregado al carrito.')
            else:
                messages.success(request, 'Sublimación guardada y producto agregado al carrito.')
            return redirect('carrito')

    related_solicitud = _latest_pending_sublimation(request.user, producto.pk)

    try:
        tasa = obtener_tasa_cambio()
    except Exception:
        tasa = 'N/A'
    try:
        precio_bs = round(float(producto.precio_venta or 0) * float(tasa), 2)
    except Exception:
        precio_bs = None

    return render(request, 'core/camisas_shein.html', {
        'producto': producto,
        'tallas': tallas,
        'default_talla': default_talla,
        'stock_por_talla': stock_por_talla,
        'es_taza': es_taza,
        'default_cantidad': 1,
        'categoria_nombre': categoria_nombre,
        'solicitud': related_solicitud,
        'sublimation_extra_cost': _sublimation_extra_cost(),
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user),
        'valor_dolar': str(tasa),
        'precio_bs': precio_bs,
    })


@login_required
def detalles_compra_producto(request, producto_id):
    """Muestra las Notas de Entrega del usuario que incluyen un producto específico."""
    producto = get_object_or_404(Producto, pk=producto_id)

    # 1. Buscamos todos los registros en CarritoDeCompras que tengan este producto
    # y pertenezcan al cliente asociado al usuario actual.
    detalles = (
        CarritoDeCompras.objects
        .filter(
            Producto=producto,
            Nota_Entrega__cliente__user=request.user
        )
        .select_related('Nota_Entrega', 'Nota_Entrega__cliente')
        .order_by('-Nota_Entrega__fecha')
    )

    # 2. Estructuramos la data para el template
    # Como cada CarritoDeCompras ya apunta a su Nota_Entrega, 
    # podemos agruparlos o listarlo directamente.
    compras = []
    for detalle in detalles:
        compras.append({
            'salida': detalle.Nota_Entrega, # Equivalente a la antigua Salida
            'items': [detalle] # El item específico que compró
        })

    # 3. Obtener la última Nota de Entrega (la más reciente)
    # Gracias al order_by('-Nota_Entrega__fecha'), el primero es el último
    latest_salida = detalles.first().Nota_Entrega if detalles.exists() else None

    return render(request, 'core/detalles_compra_producto.html', {
        'producto': producto,
        'compras': compras,
        'latest_salida': latest_salida,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True))
    })

@login_required
def historial_compras(request):
    """Muestra el historial de compras (Nota_Entrega) del usuario."""
    
    # Filtramos las notas donde el cliente asociado tiene como 'user' al usuario actual
    notas = (
        Nota_Entrega.objects
        .filter(cliente__user=request.user)  # Corregido: usar cliente__user en lugar de cliente__id
        .prefetch_related('detalles__Producto') # Trae los productos de forma eficiente
        .order_by('-fecha') # De más reciente a más antigua
    )
    total_bs= ''
    try:
        tasa= obtener_tasa_cambio()
        total_bs= sum((p.total or 0) for p in notas)* float(tasa) if tasa != 'N/A' else 'N/A'
    except Exception:
        tasa = 'N/A'
    return render(request, 'core/historial_compras.html', {
        'salidas': notas,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'total_bs': total_bs,
    })


@login_required
@admin_only
def historial_inventario(request):
    """Muestra el historial de ajustes de inventario con filtros simples."""
    try:
        qs = Historial_Inventario.objects.select_related('producto').order_by('-fecha_ajuste')

        # filtros
        q_prod = request.GET.get('producto', '').strip()
        q_user = request.GET.get('usuario', '').strip()
        q_tipo = request.GET.get('tipo', '').strip()
        date_from = request.GET.get('from', '').strip()
        date_to = request.GET.get('to', '').strip()

        if q_prod:
            qs = qs.filter(producto__nombre_producto__icontains=q_prod)
        if q_user:
            qs = qs.filter(usuario_responsable__icontains=q_user)
        if q_tipo:
            qs = qs.filter(tipo_movimiento__icontains=q_tipo)
        try:
            if date_from:
                d = datetime.datetime.strptime(date_from, '%Y-%m-%d')
                qs = qs.filter(fecha_ajuste__date__gte=d.date())
            if date_to:
                d2 = datetime.datetime.strptime(date_to, '%Y-%m-%d')
                qs = qs.filter(fecha_ajuste__date__lte=d2.date())
        except Exception:
            pass

        query_params = request.GET.copy()
        query_params.pop('page', None)

        paginator = Paginator(qs, 25)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'core/historial_inventario.html', {
            'history': page_obj.object_list,
            'page_obj': page_obj,
            'query_string': query_params.urlencode(),
            'filters': {
                'producto': q_prod,
                'usuario': q_user,
                'tipo': q_tipo,
                'from': date_from,
                'to': date_to,
            }
        })
    except Exception as e:
        logger.exception('Error loading historial_inventario')
        messages.error(request, 'No se pudo cargar el historial de inventario.')
        return redirect('inventario')

def comprar_producto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id, status_producto=True, cantidad_disponible__gt=0)
    producto.img_url = _safe_img_url(producto)

    if request.method == 'POST':
        try:
            cantidad = int(request.POST.get('cantidad', '1') or 1)
        except ValueError:
            cantidad = 1

        available = producto.cantidad_disponible or 0

        if cantidad <= 0 or cantidad > available:
            messages.error(request, 'La cantidad solicitada no está disponible.')
            return redirect('comprar_producto', producto_id=producto_id)

        # Procesar compra (simulada) dentro de una transacción
        try:
            with transaction.atomic():
                cliente_obj = getattr(request.user, 'cliente', None)
                solicitud = _latest_pending_sublimation(request.user, producto.pk)
                nota = Nota_Entrega.objects.create(
                    cliente=cliente_obj,
                    estado_pago='PENDIENTE',
                    fecha=timezone.now(),
                    total=float(producto.precio_venta or 0) * cantidad + (_sublimation_extra_cost(cantidad) if solicitud else 0.0)
                )
                carrito_item = CarritoDeCompras.objects.create(Nota_Entrega=nota, Producto = producto, cantidad=cantidad, status_carrito=True, precio_unitario=producto.precio_venta
                ) 
                nota.carrito_de_compras = carrito_item
                nota.save()

                if solicitud:
                    solicitud.carrito_de_compras = carrito_item
                    solicitud.nota_entrega = nota
                    solicitud.estado = 'PENDIENTE'
                    solicitud.save(update_fields=['carrito_de_compras', 'nota_entrega', 'estado'])

                # Restar inventario
                cantidad_anterior = producto.cantidad_disponible or 0
                producto.cantidad_disponible = max(0, cantidad_anterior - cantidad)
                producto.save()
                _consume_sublimation_stock(producto, solicitud.talla if solicitud else _get_session_cart_talla(request, producto.pk), cantidad)

                # Registrar en historial de inventario
                Historial_Inventario.objects.create(
                    producto=producto,
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=producto.cantidad_disponible or 0,
                    tipo_movimiento='venta',
                    motivo=f'Compra por usuario {request.user.username} (cantidad {cantidad})',
                    usuario_responsable=request.user.username
                )

                if solicitud:
                    messages.info(request, f'La sublimación agrega un recargo adicional de $ {_sublimation_extra_cost(cantidad):.2f} al pedido.')
                


            # Quitar el producto comprado del carrito en la sesión
            # Limpieza de sesión asd
            cart = request.session.get('cart', [])
            if producto.pk in cart:
                cart.remove(producto.pk)
                request.session['cart'] = cart
                request.session.modified = True
                _save_cart_snapshot_for_authenticated_user(request)

            messages.success(request, 'Nota de entrega generada exitosamente.')
            # Redirigir usando el ID de la nota (antes era salida_id)
            return redirect('pago_exitoso', salida_id=nota.pk)
        
        except Exception as e:
            messages.error(request, f'Error al procesar la compra: {e}')
            return redirect('comprar_producto', producto_id=producto_id)

    # Si se solicita como parcial (AJAX), devolver solo el formulario de compra parcial
    if request.method == 'GET' and request.GET.get('partial'):
        single = bool(request.GET.get('single'))
        return render(request, 'core/_purchase_form.html', {
            'producto': producto,
            'single_button': single
        })

    return render(request, 'core/comprar_producto.html', {
        'producto': producto,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True))
    })


@login_required
def pago_exitoso(request, salida_id):
    nota = get_object_or_404(Nota_Entrega, pk=salida_id)
    # Intentar recuperar items del carrito si existen

    tasa_guardada = float(nota.bcv or 0) if nota.bcv else 0.0
    if tasa_guardada <= 0:
        try:
            tasa_actual = obtener_tasa_cambio()
            tasa_guardada = float(tasa_actual) if tasa_actual != 'N/A' else 0.0
        except Exception:
            tasa_guardada = 0.0


    items = [
        {
            'producto': detalle.Producto,
            'cantidad_item': detalle.Cantidad,
            'sub_total_item': float(detalle.precio_unitario or 0) * float(detalle.Cantidad or 0),
            'precio_unitario': detalle.precio_unitario,
            'precio_bs': f"{float(detalle.precio_unitario or 0) * tasa_guardada:.2f}" if tasa_guardada else 'N/A',
        }
        for detalle in nota.detalles.all().select_related('Producto')
    ]

    sublimation_charge = 0.0
    sublimation_items = []
    for solicitud in nota.solicitudes_sublimacion.select_related('producto').all():
        try:
            charge = _sublimation_extra_cost(solicitud.cantidad)
        except Exception:
            charge = 0.0
        sublimation_charge += charge
        sublimation_items.append({
            'producto': solicitud.producto,
            'cantidad': solicitud.cantidad,
            'cargo': charge,
            'comentario': solicitud.comentario,
        })

    total = float(nota.total or 0) or (sum(item['sub_total_item'] for item in items) + sublimation_charge)

    total_bs = ''
    try:
        b = total * tasa_guardada if tasa_guardada else 'N/A'
        total_bs = f'{b:.2f}'
    

    except Exception:
        tasa_guardada = 0.0


    return render(request, 'core/pago_exitoso.html', {
        'salida': nota,  
        'items': items,
        'sublimation_items': sublimation_items,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'total_bs': total_bs,
        'total': total,


    })


@admin_only
def aprobar_pagos(request):
    if request.method == 'POST':
        salida_id = request.POST.get('salida_id')
        nuevo_estado = (request.POST.get('estado') or '').strip().upper()
        salida = get_object_or_404(Nota_Entrega, pk=salida_id, comprobante_pago__isnull=False)

        if salida.estado_pago in ['APROBADO', 'RECHAZADO']:
            messages.warning(request, f'El pago #{salida.pk} ya fue revisado y no puede modificarse.')
            return redirect('aprobar_pagos')

        total_base = float(salida.total_bruto if salida.total_bruto is not None else salida.total or 0)

        if nuevo_estado not in ['APROBADO', 'RECHAZADO']:
            messages.error(request, 'Estado no válido.')
            return redirect('aprobar_pagos')

        if nuevo_estado == 'APROBADO':
            descuento_raw = (request.POST.get('descuento_monto') or '').strip()
            motivo_descuento = ((request.POST.get('motivo_descuento') or '').strip() or 'No')[:100]
            descuento_monto = 0.0
            if descuento_raw:
                try:
                    descuento_monto = float(descuento_raw.replace(',', '.'))
                except ValueError:
                    messages.error(request, 'El monto del descuento no es válido.')
                    return redirect('aprobar_pagos')

            if descuento_monto < 0:
                messages.error(request, 'El descuento no puede ser negativo.')
                return redirect('aprobar_pagos')

            if descuento_monto > total_base:
                messages.error(request, 'El descuento no puede superar el total de la nota.')
                return redirect('aprobar_pagos')

            salida.estado_pago = "APROBADO"
            salida.motivo_rechazo = None  # Limpiar cualquier motivo de rechazo previo
            salida.descuento_monto = descuento_monto
            salida.descuento_motivo = motivo_descuento
            salida.total_bruto = total_base
            salida.total = round(total_base - descuento_monto, 2)
            if descuento_monto > 0:
                messages.success(request, f'Pago #{salida.pk} aprobado con descuento de ${descuento_monto:.2f}.')
            else:
                messages.success(request, f'Pago #{salida.pk} aprobado correctamente.')
        elif nuevo_estado == 'RECHAZADO':
            motivo = request.POST.get('motivo_rechazo', '').strip()
            if not motivo:
                messages.error(request, 'Debe proporcionar un motivo para rechazar el pago.')
                return redirect('aprobar_pagos')
            salida.estado_pago = "RECHAZADO"
            salida.motivo_rechazo = motivo
            salida.descuento_monto = 0
            salida.descuento_motivo = None
            salida.total = total_base
            messages.warning(request, f'Pago #{salida.pk} marcado como rechazado.')

        salida.revisado_por = request.user
        salida.fecha_revision = timezone.now()
        salida.save(update_fields=['estado_pago', 'motivo_rechazo', 'descuento_monto', 'descuento_motivo', 'total_bruto', 'total', 'revisado_por', 'fecha_revision'])
        return redirect('aprobar_pagos')

        salida.revisado_por = request.user
        salida.fecha_revision = timezone.now()
        salida.save(update_fields=['estado_pago', 'motivo_rechazo', 'descuento_monto', 'descuento_motivo', 'total_bruto', 'total', 'revisado_por', 'fecha_revision'])
        return redirect('aprobar_pagos')

    try:
        status_filter = request.GET.get('status', '').strip()
        queryset = (
            Nota_Entrega.objects
            .filter(comprobante_pago__isnull=False)
            .select_related('cliente', 'cliente__user', 'revisado_por')
            .prefetch_related('detalles__Producto', 'detalles__solicitudes_sublimacion')
            .order_by('-fecha', '-id')
        )
        if status_filter:
            queryset = queryset.filter(estado_pago=status_filter.upper())
        
        total_pendientes = Nota_Entrega.objects.filter(comprobante_pago__isnull=False, estado_pago='PENDIENTE').count()
        total_registros = queryset.count()
        paginator = Paginator(queryset, 5)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        if page_obj and page_obj.object_list:
            for salida in page_obj.object_list:
                salida.comprobante_url = _safe_file_url(getattr(salida, 'comprobante_pago', None))
    except Exception as e:
        logger.error(f'Error al cargar pagos: {e}', exc_info=True)
        page_obj = None
        total_pendientes = 0
        total_registros = 0

    return render(request, 'core/aprobar_pagos.html', {
        'salidas': page_obj,
        'page_obj': page_obj,
        'paginator': paginator if total_registros else None,
        'total_pendientes': total_pendientes,
        'total_registros': total_registros,
        'status_filter': status_filter,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user),
    })


@admin_only
def ordenes_sublimacion(request):
    if request.method == 'POST':
        solicitud_id = request.POST.get('solicitud_id')
        accion = (request.POST.get('accion') or '').strip().lower()
        solicitud = get_object_or_404(SolicitudSublimacion, pk=solicitud_id, nota_entrega__isnull=False)

        if accion == 'aprobar':
            solicitud.estado = 'VINCULADA'
            messages.success(request, f'Orden de sublimacion #{solicitud.pk} aprobada correctamente.')
        elif accion == 'rechazar':
            solicitud_pk = solicitud.pk
            solicitud.delete()
            messages.warning(request, f'Orden de sublimacion #{solicitud_pk} rechazada y eliminada.')
            return redirect('ordenes_sublimacion')
        elif accion == 'pendiente':
            solicitud.estado = 'PENDIENTE'
            messages.info(request, f'Orden de sublimacion #{solicitud.pk} movida a pendiente.')
        else:
            messages.error(request, 'Accion no valida.')
            return redirect('ordenes_sublimacion')

        solicitud.save(update_fields=['estado'])
        return redirect('ordenes_sublimacion')

    try:
        search_query = (request.GET.get('q') or '').strip()
        estado_filter = (request.GET.get('estado') or '').strip().upper()
        estado_pago_filter = (request.GET.get('estado_pago') or '').strip().upper()

        queryset = (
            SolicitudSublimacion.objects
            .filter(nota_entrega__isnull=False)
            .select_related('usuario', 'producto', 'nota_entrega', 'nota_entrega__cliente')
        )

        if search_query:
            queryset = queryset.filter(
                Q(producto__nombre_producto__icontains=search_query)
                | Q(usuario__username__icontains=search_query)
                | Q(nota_entrega__cliente__nombre_cliente__icontains=search_query)
                | Q(nota_entrega__cliente__apellido_cliente__icontains=search_query)
                | Q(nota_entrega__cliente__telefono_cliente__icontains=search_query)
                | Q(comentario__icontains=search_query)
                | Q(nota_entrega__pk__iexact=search_query)
            )

        if estado_filter in {'PENDIENTE', 'VINCULADA', 'RECHAZADA'}:
            queryset = queryset.filter(estado=estado_filter)

        if estado_pago_filter in {'PENDIENTE', 'APROBADO', 'RECHAZADO'}:
            queryset = queryset.filter(nota_entrega__estado_pago=estado_pago_filter)

        queryset = queryset.order_by('-creado_en', '-id')
        total_ordenes = queryset.count()
        pendientes_revision = queryset.filter(estado='PENDIENTE').count()
        per_page = max(total_ordenes, 1)
        paginator = Paginator(queryset, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Resolver URLs de imagen de forma segura para evitar errores de storage en template.
        for solicitud in page_obj.object_list:
            solicitud.producto_img_url = _safe_img_url(solicitud.producto)
            solicitud.diseno_url = _safe_file_url(getattr(solicitud, 'imagen_sublimacion', None))
    except Exception as e:
        logger.error(f'Error al cargar ordenes de sublimacion: {e}', exc_info=True)
        page_obj = None
        total_ordenes = 0
        pendientes_revision = 0
        paginator = None

    query_string = request.GET.copy()
    query_string.pop('page', None)

    return render(request, 'core/ordenes_sublimacion.html', {
        'page_obj': page_obj,
        'paginator': paginator,
        'total_ordenes': total_ordenes,
        'pendientes_revision': pendientes_revision,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user),
        'search_query': search_query,
        'estado_filter': estado_filter,
        'estado_pago_filter': estado_pago_filter,
        'query_string': query_string.urlencode(),
    })


@login_required
def detalles_salida(request, salida_id):
    """Mostrar todos los productos incluidos en una Nota de Entrega (antes Salida) específica."""
    nota = get_object_or_404(Nota_Entrega, pk=salida_id)
    

    items = [
        {
            'producto': detalle.Producto,
            'cantidad_item': detalle.Cantidad,
            'sub_total_item': float(detalle.precio_unitario or 0) * float(detalle.Cantidad or 0),
            'precio_unitario': detalle.precio_unitario,
        }
        for detalle in nota.detalles.all().select_related('Producto')
    ]
    
    # Retornamos al template
    return render(request, 'core/detalles_salida.html', {
        'salida': nota,  # Mantenemos 'salida' para que el template siga funcionando sin cambios masivos
        'items': items,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True))
    })

@login_required
def comprar_carrito(request):
    if request.method != 'POST':
        return redirect('carrito')

    cart = request.session.get('cart', []) or []
    if not cart:
        messages.error(request, 'No hay productos en el carrito.')
        return redirect('carrito')

    documento = (request.POST.get('documento') or '').strip()
    mobile_phone = (request.POST.get('mobile_phone') or '').strip()
    referencia = (request.POST.get('referencia') or '').strip()
    if not documento:
        messages.error(request, 'Debes ingresar la cédula o documento.')
        return redirect('pago_movil')
    if not mobile_phone:
        messages.error(request, 'Debes ingresar el teléfono de pago móvil.')
        return redirect('pago_movil')
    if not mobile_phone.isdigit():
        messages.error(request, 'El teléfono debe contener solo números.')
        return redirect('pago_movil')
    if len(mobile_phone) < 10 or len(mobile_phone) > 11:
        messages.error(request, 'El teléfono debe tener entre 10 y 11 dígitos.')
        return redirect('pago_movil')
    if not referencia:
        messages.error(request, 'Debes ingresar la referencia de pago.')
        return redirect('pago_movil')

    payment_proof = request.FILES.get('payment_proof')
    if not payment_proof:
        messages.error(request, 'Debes subir el comprobante de pago.')
        return redirect('pago_movil')

    saved_proof_path = None
    content_type = (payment_proof.content_type or '').lower()
    if not content_type.startswith('image/'):
        messages.error(request, 'El comprobante debe ser una imagen valida.')
        return redirect('pago_movil')

    if payment_proof.size > (5 * 1024 * 1024):
        messages.error(request, 'El comprobante supera el tamano maximo de 5 MB.')
        return redirect('pago_movil')

    payment_proof = optimize_uploaded_image(payment_proof, max_size=(1600, 1600), quality=82)

    _, ext = os.path.splitext(payment_proof.name or '')
    ext = (ext or '.jpg').lower()
    proof_name = f"payment_proofs/{request.user.pk}_{timezone.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
    try:
        saved_proof_path = default_storage.save(proof_name, payment_proof)
    except Exception:
        messages.error(request, 'No se pudo guardar la imagen del comprobante.')
        return redirect('pago_movil')

    productos = Producto.objects.filter(pk__in=cart)

    # Depuración: registrar sesión/carrito y claves de cantidades enviadas para diagnosticar qty faltantes.
    try:
        logger.info('comprar_carrito invoked: user=%s cart=%s post_keys=%s files=%s',
                    getattr(request.user, 'username', None),
                    cart,
                    list(request.POST.keys()),
                    list(request.FILES.keys()))
    except Exception:
        logger.exception('Failed to log comprar_carrito debug info')

    tasa = obtener_tasa_cambio()
    valor_bcv = float(tasa) if tasa != 'N/A' else 0.00

    try:
        with transaction.atomic():
            # PASO 1: Obtener cliente y crear la cabecera (Nota_Entrega)
            cliente_obj = getattr(request.user, 'cliente', None)
            #cliente_obj = getattr(request.user, 'cliente', None)
            
            metodo_pago = MetodoPago.objects.filter(nombre_metodo_pago__iexact='Pago Móvil').first() or MetodoPago.objects.filter(nombre_metodo_pago__iexact='PAGO MOVIL').first()
            nota = Nota_Entrega.objects.create(
                cliente=cliente_obj,
                estado_pago='PENDIENTE',
                fecha=timezone.now(),
                total=0.0,
                total_bruto=0.0,
                bcv=valor_bcv,
                tipo_pago='PAGO MOVIL',
                metodo_pago=metodo_pago,
                #cliente_id=documento[:45],
                cliente_telefono=mobile_phone[:15],
                referencia_pago=referencia,
            )
            logger.info(f'Nota_Entrega creada: {nota.pk} para usuario {request.user.username}')
            
            total_acumulado = 0.0

            # PASO 2: Procesar cada producto del carrito
            for p in productos:
                qty = request.POST.get(f'cantidad_{p.pk}') or request.POST.get(f'qty_{p.pk}') or request.POST.get(str(p.pk)) or 1
                try:
                    cantidad = int(qty)
                except Exception:
                    cantidad = 1

                available = int(p.cantidad_disponible or 0)
                using_talla_stock = False

                # Si producto.cantidad_disponible no alcanza pero hay stock por talla (ej. Tazas 'Unica'),
                # permitir consumir desde ProductoTallaStock y continuar.
                if cantidad > available:
                    try:
                        talla_total = ProductoTallaStock.objects.filter(producto=p).aggregate(total=__import__('django').db.models.Sum('stock_disponible'))
                        total_talla_stock = int((talla_total.get('total') or 0) if isinstance(talla_total, dict) else (talla_total or 0))
                    except Exception:
                        total_talla_stock = 0

                    if total_talla_stock >= cantidad:
                        using_talla_stock = True
                    else:
                        messages.error(request, f'Cantidad no disponible para {p.nombre_producto}.')
                        raise ValueError('stock insuficiente')

                subtotal = float(p.precio_venta or 0) * cantidad
                solicitud = _latest_pending_sublimation(request.user, p.pk)
                costo_sublimacion = _sublimation_extra_cost(cantidad) if solicitud else 0.0
                
                # PASO 3: Crear el detalle en CarritoDeCompras vinculado a la Nota
                CarritoDeCompras.objects.create(
                    Nota_Entrega=nota,
                    Producto=p,
                    Cantidad=cantidad,
                    talla=_get_session_cart_talla(request, p.pk),
                    precio_unitario=p.precio_venta,
                    status_carrito=True
                )

                if solicitud:
                    solicitud.carrito_de_compras = CarritoDeCompras.objects.filter(Nota_Entrega=nota, Producto=p).order_by('-id').first()
                    solicitud.nota_entrega = nota
                    solicitud.estado = 'PENDIENTE'
                    solicitud.save(update_fields=['carrito_de_compras', 'nota_entrega', 'estado'])

                # PASO 4: Actualizar inventario e historial
                cant_anterior = int(p.cantidad_disponible or 0)

                if using_talla_stock:
                    # Consumir primero desde stock por talla (distribuir entre registros hasta completar)
                    remaining = cantidad
                    for st in ProductoTallaStock.objects.filter(producto=p).order_by('-stock_disponible'):
                        available_st = int(st.stock_disponible or 0)
                        if available_st <= 0:
                            continue
                        take = min(available_st, remaining)
                        st.stock_disponible = max(0, available_st - take)
                        st.save(update_fields=['stock_disponible'])
                        remaining -= take
                        if remaining <= 0:
                            break

                    # También decrementar producto.cantidad_disponible para mantener sincronía
                    p.cantidad_disponible = max(0, cant_anterior - cantidad)
                    p.save()
                    # Si hay talla en sesión, llamar _consume_sublimation_stock por compatibilidad; si no, omitir
                    try:
                        sel_talla = _get_session_cart_talla(request, p.pk)
                        if sel_talla:
                            _consume_sublimation_stock(p, sel_talla, cantidad)
                    except Exception:
                        logger.exception('Error consuming sublimation stock fallback for product %s', p.pk)

                else:
                    p.cantidad_disponible = max(0, cant_anterior - cantidad)
                    p.save()
                    # consume talla-specific stock if talla present
                    try:
                        _consume_sublimation_stock(p, _get_session_cart_talla(request, p.pk), cantidad)
                    except Exception:
                        logger.exception('Error consuming sublimation stock for product %s', p.pk)

                Historial_Inventario.objects.create(
                    producto=p,
                    cantidad_anterior=cant_anterior,
                    cantidad_nueva=int(p.cantidad_disponible or 0),
                    tipo_movimiento='venta',
                    motivo=f'Venta múltiple - Nota #{nota.id}',
                    usuario_responsable=request.user.username
                )

                total_acumulado += subtotal + costo_sublimacion

            # PASO 5: Actualizar el total final de la Nota
            nota.total_bruto = total_acumulado
            nota.total = total_acumulado
            if saved_proof_path:
                nota.comprobante_pago = saved_proof_path
                logger.info(f'Comprobante asignado a nota {nota.pk}: {saved_proof_path}')
            nota.save()
            logger.info(f'Nota {nota.pk} guardada con total {total_acumulado}')

            request.session['cart'] = []
            request.session['cart_options'] = {}
            request.session.modified = True
            _clear_cart_snapshot_for_user(request.user)

            messages.success(request, f'Pago móvil registrado correctamente. Orden #{nota.pk} enviada a revisión.')

    except ValueError:
        return redirect('carrito')
    except Exception as e:
        logger.error(f'Error en comprar_carrito para usuario {request.user.username}: {e}', exc_info=True)
        messages.error(request, f'Error al procesar la compra: {e}')
        return redirect('carrito')

    return redirect('pago_exitoso', salida_id=nota.pk)

@login_required
def pago_movil(request):
    """Mostrar la pantalla de pago móvil (recibe cantidades desde el formulario del carrito y no finaliza la compra).
    El formulario resultante enviará los datos a `comprar_carrito` para finalizar la compra incluyendo los campos
    `documento` y `mobile_phone` y `mobile_paid`.
    """
    if request.method != 'POST':
        return redirect('carrito')

    cart = request.session.get('cart', []) or []
    if not cart:
        messages.error(request, 'No hay productos en el carrito.')
        return redirect('carrito')

    #  variables por defecto
    cedula = ''
    telefono = ''


    try:
        # Intentamos acceder al perfil de cliente directamente conectado a este usuario
        cliente = request.user.cliente
        cedula = getattr(cliente, 'documento', '') or ''
        telefono = getattr(cliente, 'telefono_cliente', None) or getattr(cliente, 'telefono', '') or ''
        
    except ObjectDoesNotExist:
        # Si el usuario no tiene perfil de cliente, se queda con los valores vacíos
        pass 

    productos = Producto.objects.filter(pk__in=cart)
    items = []
    total = 0.0

    # recoger cantidades desde request.POST
    for p in productos:
        qty = request.POST.get(f'cantidad_{p.pk}') or request.POST.get(f'qty_{p.pk}') or request.POST.get(str(p.pk)) or 1
        
        try:
            cantidad = int(qty)
        except (ValueError, TypeError): # Capturamos solo los errores de conversión
            cantidad = 1
            
        subtotal = float(p.precio_venta or 0) * cantidad
        solicitud = _latest_pending_sublimation(request.user, p.pk)
        costo_sublimacion = _sublimation_extra_cost(cantidad) if solicitud else 0.0
        total_linea = subtotal + costo_sublimacion
        
        items.append({
            'producto': p, 
            'cantidad': cantidad,
            'precio_bs': total_linea * float(obtener_tasa_cambio() or 'N/A') if total_linea and obtener_tasa_cambio() else 'N/A',
            'subtotal': subtotal, 
            'costo_sublimacion': costo_sublimacion,
            'total_linea': total_linea,
            'talla': _get_session_cart_talla(request, p.pk), 
            'sublimacion': solicitud
        })
        total += total_linea
    
    total_bs = ''
    try:
        tasa= obtener_tasa_cambio()
        b= total* float(tasa) if tasa != 'N/A' else 'N/A'
        total_bs = f'{b:.2f}'
    except Exception:
        tasa = 'N/A'

    return render(request, 'core/pago_movil.html', {
        'items': items,
        'total': total,
        'post': request.POST, # Se envía para re-renderizar inputs ocultos si es necesario
        'cart_count': len(cart),
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'cedula': cedula,
        'telefono': telefono,
        'valor_dolar': str(tasa),
        'total_bs': total_bs,

    })



@login_required
def comprar_producto_ajax(request, producto_id):
    """Procesa la compra de un solo producto vía AJAX usando Nota_Entrega."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    producto = get_object_or_404(Producto, pk=producto_id, status_producto=True, cantidad_disponible__gt=0)
    try:
        cantidad = int(request.POST.get('cantidad', '1') or 1)
    except Exception:
        cantidad = 1

    available = producto.cantidad_disponible or 0
    if cantidad <= 0 or cantidad > available:
        return JsonResponse({'success': False, 'error': 'Cantidad no disponible'}, status=400)

    try:
        with transaction.atomic():
            # PASO 1: Crear la Nota de Entrega (Cabecera)
            cliente_obj = getattr(request.user, 'cliente', None)
            subtotal = float(producto.precio_venta or 0) * cantidad
            tasa = obtener_tasa_cambio()
            valor_bcv = float(tasa) if tasa != 'N/A' else 0.00
            solicitud = _latest_pending_sublimation(request.user, producto.pk)
            costo_sublimacion = _sublimation_extra_cost(cantidad) if solicitud else 0.0
            
            nota = Nota_Entrega.objects.create(
                cliente=cliente_obj,
                estado_pago='PENDIENTE',
                total=subtotal + costo_sublimacion,
                total_bruto=subtotal + costo_sublimacion,
                bcv=valor_bcv,
                fecha=timezone.now()
            )

            # PASO 2: Crear el detalle en CarritoDeCompras vinculado a la Nota
            item_carrito = CarritoDeCompras.objects.create(
                Nota_Entrega=nota,
                Producto=producto,
                Cantidad=cantidad,
                talla=request.POST.get('talla') or _get_session_cart_talla(request, producto.pk),
                precio_unitario=producto.precio_venta,
                status_carrito=True
            )

            if solicitud:
                solicitud.carrito_de_compras = item_carrito
                solicitud.nota_entrega = nota
                solicitud.estado = 'PENDIENTE'
                solicitud.save(update_fields=['carrito_de_compras', 'nota_entrega', 'estado'])

            # PASO 3: Actualizar inventario
            cantidad_anterior = producto.cantidad_disponible or 0
            producto.cantidad_disponible = max(0, cantidad_anterior - cantidad)
            producto.save()
            _consume_sublimation_stock(producto, item_carrito.talla, cantidad)

            # PASO 4: Registrar historial de inventario
            Historial_Inventario.objects.create(
                producto=producto,
                cantidad_anterior=cantidad_anterior,
                cantidad_nueva=producto.cantidad_disponible,
                tipo_movimiento='venta',
                motivo=f'Compra AJAX (Nota #{nota.id})',
                usuario_responsable=request.user.username
            )

            # PASO 5: Limpiar el producto de la sesión si existía
            try:
                cart = request.session.get('cart', []) or []
                if producto.pk in cart:
                    cart.remove(producto.pk)
                    request.session['cart'] = cart
                    cart_options = request.session.get('cart_options', {}) or {}
                    cart_options.pop(str(producto.pk), None)
                    request.session['cart_options'] = cart_options
                    request.session.modified = True
                    _save_cart_snapshot_for_authenticated_user(request)
            except Exception:
                pass

        # Retornar éxito con el ID de la nota
        return JsonResponse({'success': True, 'nota_id': nota.pk})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def clear_cart(request):
    """Vacía el carrito en la sesión del usuario y redirige al carrito."""
    try:
        request.session['cart'] = []
        request.session['cart_options'] = {}
        request.session.modified = True
    except Exception:
        request.session.pop('cart', None)
        request.session.pop('cart_options', None)
    _clear_cart_snapshot_for_user(request.user)
    messages.success(request, 'Se han eliminado todos los productos del carrito.')
    return redirect('carrito')

@login_required
@admin_only
def eliminar_producto(request, producto_id):
    if request.method == 'POST':
        try:
            producto = get_object_or_404(Producto, pk=producto_id)
            nombre_producto = producto.nombre_producto

            # Producto.PROTECT via CarritoDeCompras: si todavía hay referencias,
            # no intentamos borrar para evitar un error de base de datos.
            if CarritoDeCompras.objects.filter(Producto_id=producto_id).exists():
                messages.error(
                    request,
                    f'No se puede eliminar "{nombre_producto}" porque todavía tiene registros asociados en el carrito o pedidos.',
                )
                return redirect('inventario')

            producto.delete()
            # Asegurar limpieza del carrito actual en sesión (quitar cualquier ocurrencia del ID)
            try:
                cart = request.session.get('cart', [])
                if producto_id in cart:
                    cart = [pid for pid in cart if pid != producto_id]
                    request.session['cart'] = cart
            except Exception:
                pass
            messages.success(request, f'El producto "{nombre_producto}" ha sido eliminado exitosamente.')
        except ProtectedError:
            messages.error(
                request,
                'No se puede eliminar este producto porque todavía tiene registros asociados.',
            )
        except Exception as e:
            messages.error(request, f'Error al eliminar el producto: {str(e)}')
    
    return redirect('inventario')


@login_required
@admin_only
def cambiar_estado_producto(request, producto_id):
    if request.method != 'POST':
        return redirect('inventario')

    producto = get_object_or_404(Producto, pk=producto_id)
    status_raw = (request.POST.get('status_producto') or '').strip().lower()

    if status_raw not in ('true', 'false'):
        messages.error(request, 'Estado de producto inválido.')
        return redirect('inventario')

    nuevo_estado = status_raw == 'true'
    if nuevo_estado and (producto.cantidad_disponible or 0) <= 0:
        messages.error(
            request,
            f'No se puede activar "{producto.nombre_producto}" porque no tiene stock disponible. Debe reponerse el inventario primero.'
        )
        return redirect('inventario')

    producto.status_producto = nuevo_estado
    producto.save(update_fields=['status_producto'])

    mensajes = 'activado' if nuevo_estado else 'inactivado'
    messages.success(request, f'El producto "{producto.nombre_producto}" ha sido {mensajes} correctamente.')
    return redirect('inventario')

@login_required
@admin_only
def ajustar_inventario(request, producto_id):
    if request.method == 'POST':
        try:
            producto = get_object_or_404(Producto, pk=producto_id)
            tipo_ajuste = request.POST.get('tipo_ajuste')
            cantidad_ajuste = int(request.POST.get('cantidad_ajuste', 0))
            motivo = request.POST.get('motivo', '')
            
            cantidad_anterior = producto.cantidad_disponible or 0
            
            if tipo_ajuste == 'agregar':
                producto.cantidad_disponible = cantidad_anterior + cantidad_ajuste
            elif tipo_ajuste == 'quitar':
                producto.cantidad_disponible = max(0, cantidad_anterior - cantidad_ajuste)
            elif tipo_ajuste == 'establecer':
                producto.cantidad_disponible = cantidad_ajuste
            
            producto.save()
            if (producto.cantidad_disponible or 0) <= 0:
                messages.warning(
                    request,
                    f'"{producto.nombre_producto}" quedó inactivo automáticamente porque no tiene stock disponible.'
                )
            # Registrar en historial de inventario
            try:
                if producto.cantidad_disponible > cantidad_anterior:
                    tipo = 'Ajuste Positivo'
                elif producto.cantidad_disponible < cantidad_anterior:
                    tipo = 'Ajuste Negativo'
                else:
                    tipo = 'Sin Cambio'

                Historial_Inventario.objects.create(
                    producto=producto,
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=producto.cantidad_disponible,
                    tipo_movimiento=tipo,
                    motivo=motivo or 'Sin motivo especificado',
                    usuario_responsable=str(request.user)
                )
            except Exception:
                # No bloquear la ejecución si falla el historial
                pass
            
            # Crear mensaje descriptivo
            tipo_texto = {
                'agregar': 'agregadas',
                'quitar': 'quitadas',
                'establecer': 'establecidas'
            }.get(tipo_ajuste, 'ajustadas')
            
            messages.success(
                request, 
                f'Inventario ajustado: {cantidad_ajuste} unidades {tipo_texto} al producto "{producto.nombre_producto}". '
                f'Cantidad anterior: {cantidad_anterior}, Cantidad nueva: {producto.cantidad_disponible}.'
            )
            
        except Exception as e:
            messages.error(request, f'Error al ajustar el inventario: {str(e)}')
    
    return redirect('inventario')

@login_required
@admin_only

def editar_producto(request, producto_id):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, pk=producto_id)

        # Capturamos valores propensos a error fuera del bloque de transacción para validarlos
        try:
            cantidad_anterior = producto.cantidad_disponible
            nueva_cantidad = cantidad_anterior or 0

            # Lo mismo para el precio
            precio_raw = request.POST.get('precio_venta')
            nuevo_precio = float(precio_raw) if precio_raw else producto.precio_venta

        except ValueError:
            messages.error(request, 'Error: El precio debe ser un número válido.')
            return redirect('inventario')

        # Prevalidación: exigir motivo no vacío si cambia cualquier campo editable
        motivo = (request.POST.get('motivoAjuste') or '').strip()

        # Determinar valores enviados para comparación
        posted_nombre = (request.POST.get('nombre_producto') or '').strip()
        posted_desc = (request.POST.get('descripcion') or '').strip()
        posted_precio = nuevo_precio
        posted_cantidad = producto.cantidad_disponible or 0
        categoria_id = request.POST.get('categoria')
        try:
            posted_categoria_id = int(categoria_id) if categoria_id and categoria_id.isdigit() else (producto.categoria_id if getattr(producto, 'categoria_id', None) is not None else None)
        except Exception:
            posted_categoria_id = producto.categoria_id if getattr(producto, 'categoria_id', None) is not None else None
        posted_imagen = bool(request.FILES.get('imagen_producto'))

        changed = False
        changed_non_image = False
        if posted_nombre and posted_nombre != (producto.nombre_producto or ''):
            changed = True
            changed_non_image = True
        if posted_desc != (producto.descripcion or ''):
            changed = True
            changed_non_image = True
        # Comparar numéricos con tolerancia para flotantes
        try:
            if float(posted_precio) != float(producto.precio_venta or 0):
                changed = True
                changed_non_image = True
        except Exception:
            pass
        if posted_categoria_id != (producto.categoria_id if getattr(producto, 'categoria_id', None) is not None else None):
            changed = True
            changed_non_image = True
        if posted_imagen:
            changed = True

        # Permitir actualizar solo la imagen sin exigir motivo.
        if changed_non_image and not motivo:
            messages.error(request, 'Debes proporcionar un motivo cuando realizas cualquier cambio al producto.')
            return redirect('inventario')

        try:
            # Usamos atomic para asegurar que se guarde EL PRODUCTO Y EL HISTORIAL juntos
            with transaction.atomic():

                # 1. Actualizamos datos del producto
                producto.nombre_producto = request.POST.get('nombre_producto', producto.nombre_producto)
                producto.descripcion = request.POST.get('descripcion', producto.descripcion)
                producto.precio_venta = nuevo_precio

                # El stock no se modifica aquí. Los cambios de cantidad deben hacerse desde Ajustar Inventario.

                # Lógica de categoría
                if categoria_id:
                    if categoria_id.isdigit(): # Validación extra
                        producto.categoria_id = int(categoria_id) # Asignación directa por ID es más rápida

                if request.FILES.get('imagen_producto'):
                    producto.imagen_producto = request.FILES['imagen_producto']

                # GUARDAMOS EL PRODUCTO PRIMERO
                producto.save()

                if (producto.cantidad_disponible or 0) <= 0:
                    messages.warning(
                        request,
                        f'"{producto.nombre_producto}" quedó inactivo automáticamente porque no tiene stock disponible.'
                    )

                # Diagnóstico para verificar ruta y URL final de imagen en producción.
                if producto.imagen_producto and producto.imagen_producto.name:
                    try:
                        resolved_url = _safe_img_url(producto)
                    except Exception:
                        resolved_url = 'ERROR_RESOLVING_URL'
                    logger.info(
                        'Producto imagen actualizada | producto_id=%s image_name=%s resolved_url=%s',
                        producto.pk,
                        producto.imagen_producto.name,
                        resolved_url,
                    )

                # 2. Lógica del historial
                if nueva_cantidad > cantidad_anterior:
                    tipo = 'Ajuste Positivo'
                elif nueva_cantidad < cantidad_anterior:
                    tipo = 'Ajuste Negativo'
                else:
                    tipo = 'Sin Cambio'

                # CREAMOS EL HISTORIAL (Solo si hubo cambio o si quieres registrar todo evento)
                Historial_Inventario.objects.create(
                    producto=producto,
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=nueva_cantidad,
                    tipo_movimiento=tipo,
                    motivo=motivo or 'Sin motivo especificado',
                    usuario_responsable=str(request.user)
                )

            # Si todo sale bien dentro del "with transaction.atomic()", llegamos aquí:
            messages.success(request, f'Producto "{producto.nombre_producto}" actualizado exitosamente.')

        except Exception as e:
            # Imprimir el error en la consola te ayudará a ver qué pasó realmente
            print(f"Error detallado: {e}") 
            error_text = str(e)
            if 'Unknown API key' in error_text or 'api_key' in error_text:
                messages.error(
                    request,
                    'Error al subir la imagen: credenciales de Cloudinary inválidas. '
                    'Revisa CLOUDINARY_* o usa almacenamiento local.'
                )
            else:
                messages.error(request, f'Error al actualizar el producto: {error_text}')

    return redirect('inventario')

@login_required
@admin_only
def todos_clientes(request):
    # Filtros
    nombre = request.GET.get('nombre', '').strip()
    apellido = request.GET.get('apellido', '').strip()
    documento = request.GET.get('documento', '').strip()
    telefono = request.GET.get('telefono', '').strip()
    email = request.GET.get('email', '').strip()

    clientes_qs = Cliente.objects.only(
        'id', 'nombre_cliente', 'apellido_cliente', 'telefono_cliente', 'email'
    )

    # Aplicar filtros
    if nombre:
        clientes_qs = clientes_qs.filter(nombre_cliente__icontains=nombre)
    if apellido:
        clientes_qs = clientes_qs.filter(apellido_cliente__icontains=apellido)
    if documento:
        clientes_qs = clientes_qs.filter(id__icontains=documento)
    if telefono:
        clientes_qs = clientes_qs.filter(telefono_cliente__icontains=telefono)
    if email:
        clientes_qs = clientes_qs.filter(email__icontains=email)

    clientes_qs = clientes_qs.order_by('nombre_cliente')

    paginator = Paginator(clientes_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    cart_session = request.session.get('cart', {})
    if isinstance(cart_session, dict):
        cart_count = sum((item or {}).get('cantidad', 0) for item in cart_session.values())
    else:
        cart_count = len(cart_session)

    return render(request, 'core/clientes.html', {
        'clientes': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'cart_count': cart_count,
        'user_groups': _user_groups(request.user),
        # Pasar filtros para mantenerlos en el formulario
        'filtros': {
            'nombre': nombre,
            'apellido': apellido,
            'documento': documento,
            'telefono': telefono,
            'email': email,
        }
    })


@login_required
@admin_only
@require_POST
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    nombre_cliente = str(cliente)
    cliente.delete()
    messages.success(request, f'Cliente "{nombre_cliente}" eliminado correctamente.')

    next_url = (request.POST.get('next') or '').strip()
    if next_url:
        return redirect(next_url)
    return redirect('todos_clientes')

@login_required
@admin_only
def agregar_marca(request):
    marcas_qs = Marca_producto.objects.all().order_by('nombre_marca')
    paginator = Paginator(marcas_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        nueva_marca = request.POST.get('marca_producto', '').strip().upper()
        if nueva_marca:
            try:
                Marca_producto.objects.create(nombre_marca=nueva_marca)
                messages.success(request, f'Marca "{nueva_marca}" agregada correctamente.')
            except IntegrityError:
                messages.error(request, f'La marca "{nueva_marca}" ya existe.')
        
            except Exception as e:
                messages.error(request, f'Error al agregar la marca: {str(e)}')
        else:
            messages.error(request, 'Debes ingresar el nombre de la marca.')
        return redirect('agregar_marca')
    
    return render(request, 'core/agregar_marca.html', {
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'marcas_page': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    })

def respuesta_bloqueo_login(request, credentials, *args, **kwargs):
    """
    Esta función se ejecuta automáticamente cuando Axes bloquea un acceso.
    Renderiza la misma página de login, pero inyecta una variable de bloqueo.
    """
    # 1. Instanciamos un formulario vacío para que el HTML no falle
    form = AuthenticationForm()
    
    # 2. Preparamos el contexto con una bandera (flag) que avise del bloqueo
    context = {
        'form': form,
        'usuario_bloqueado': True,
    }
    
    # 3. Renderizamos la plantilla original de tu login con un código de error 403
    return render(request, 'core/index.html', context,)