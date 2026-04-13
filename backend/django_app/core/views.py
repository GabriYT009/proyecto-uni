import logging
from collections import Counter
from django.views import View
from django.template.loader import render_to_string

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib.auth.models import User, Group
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, F, Case, When, IntegerField
from django.core.cache import cache
from django.conf import settings
import re
import os
import json
from .models import Producto, Cliente, Categoria, Historial_Inventario, MetodoPago, CarritoDeCompras, OrdenDeDespacho
from django.core.paginator import Paginator
from .forms import ProductForm
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
from django.core.files.storage import default_storage

from .bcv import obtener_tasa_cambio
from .NotaE import Generar_NE

from .models import Producto, Nota_Entrega, CarritoDeCompras, Historial_Inventario, Cliente

def is_admin(user):
    if not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return False
    return user.groups.filter(name='admin').exists()

def admin_only(view_func):
    decorated_view_func = user_passes_test(is_admin, login_url='login')(login_required(view_func))
    return decorated_view_func

@login_required
@admin_only
def ajustar_inventario_masivo(request):
    productos = Producto.objects.all().order_by('nombre_producto')
    return render(request, 'core/ajustar_inventario.html', {'productos': productos})


logger = logging.getLogger(__name__)

HOME_PRODUCTS_LIMIT = 24
ALLOWED_CATEGORY_NAMES = [
    'Cajas',
    'Toppers',
    'Sublimación',
    'Impresión',
    'Personalización',
    'Papelería',
]


def _safe_img_url(producto):
    fallback = settings.STATIC_URL + 'assets/img/logo.png'
    try:
        if producto.imagen_producto and producto.imagen_producto.url:
            image_name = producto.imagen_producto.name
            try:
                if producto.imagen_producto.storage.exists(image_name):
                    return producto.imagen_producto.url
            except Exception:
                pass

            image_basename = os.path.basename(image_name)
            static_fallback_path = os.path.join(settings.FRONTEND_DIR, 'static', 'product-images', image_basename)
            if os.path.exists(static_fallback_path):
                return settings.STATIC_URL + 'product-images/' + image_basename
    except Exception:
        pass
    return fallback


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
            .filter(status_producto=True)
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

        fallback_user = os.environ.get("DJANGO_ADMIN_USER", "admin1")
        fallback_pass = os.environ.get("DJANGO_ADMIN_PASSWORD", "123456")

        try:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')

            # If the DB has no users yet (fresh deployment), allow default admin credentials.
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

                try:
                    admin_group = Group.objects.get(name="admin")
                    user_obj.groups.add(admin_group)
                except Group.DoesNotExist:
                    pass

                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
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
        email = data.get('email', '').strip()
        tipo_documento = data.get('tipo_documento', '').strip()
        

        if not tipo:
            errors['id_tipo_cliente'] = 'Seleccione el tipo de cliente.'

        if not nombre:
            errors['nombre_cliente'] = 'El nombre es obligatorio.'
        else:
            if len(nombre) > 45:
                errors['nombre_cliente'] = 'El nombre no puede tener más de 45 caracteres.'
            elif re.search(r'\d', nombre):
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

        # Validar teléfono (si fue suministrado): solo dígitos y hasta 11 caracteres
        if telefono:
            if not telefono.isdigit():
                errors['telefono_cliente'] = 'El teléfono debe contener solo números.'
            elif len(telefono) > 11:
                errors['telefono_cliente'] = 'El teléfono no puede tener más de 11 dígitos.'

        if not email:
            errors['email'] = 'El correo electrónico es obligatorio.'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = 'El correo electrónico no tiene un formato válido.'

        # Validaciones por tipo de cliente
        if tipo == '1':
            cedula = data.get('cedula_dni', '').strip()
            if not cedula:
                errors['cedula_dni'] = 'La cédula es obligatoria para persona natural.'
            elif not cedula.isdigit():
                errors['cedula_dni'] = 'La cédula debe contener solo números.'
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
                elif len(ced_rep) > 11:
                    errors['cedula_dni_representante'] = 'La cédula del representante no puede tener más de 11 dígitos.'

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
                # Persona natural: guardar cédula en `documento`
                if tipo_documento == 'V':
                    cliente_kwargs['documento'] = 'V' + data.get('cedula_dni','').strip()
                elif tipo_documento == 'E':
                    cliente_kwargs['documento'] = 'E' + data.get('cedula_dni','').strip()
                    
            elif tipo == '2':
                # Persona jurídica: guardar RIF en `rif_empresarial` y nombre de empresa en `nombre_cliente`
                rif_val = form_data.get('rif_empresa', '').strip()
                nombre_emp = data.get('nombre_empresa','').strip()
                if rif_val:
                    cliente_kwargs['rif_empresarial'] = rif_val
                if nombre_emp:
                    cliente_kwargs['nombre_cliente'] = nombre_emp
                # si existe cédula representante la guardamos en `documento` opcionalmente
                ced_rep = data.get('cedula_dni_representante','').strip()
                if ced_rep:
                    cliente_kwargs['documento'] = ced_rep

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
    if request.method == 'POST':
        # 1. Obtener datos del formulario
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password2') # Corregido nombre variable para claridad
        
        # Datos para el modelo Cliente
        cedula = str(request.POST.get('tipo_documento')+request.POST.get('cedula_dni')).strip()  
        nombre = request.POST.get('nombre_cliente')
        apellido = request.POST.get('apellido_cliente')
        direccion = request.POST.get('direccion') # Ojo con el acento en el HTML name='dirección' o 'direccion'
        telefono = request.POST.get('telefono_cliente')
        
        # email 
        email = request.POST.get('email') or request.session.get('pending_email')

        # -- VALIDACIONES --
        if not username or not password:
            return render(request, 'core/crear_usuario.html', {'error': 'Usuario y contraseña obligatorios.'})
        
        if password != password_confirm:
            return render(request, 'core/crear_usuario.html', {'error': 'Las contraseñas no coinciden.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'core/crear_usuario.html', {'error': 'El usuario ya existe.'})

        if User.objects.filter(email=email).exists():
            return render(request, 'core/crear_usuario.html', {'error': 'El correo ya está registrado.'})

        # CREACIÓN (Usamos atomic para que se creen los dos o ninguno) 
        try:
            with transaction.atomic():
                # A. Crear el Usuario de Django
                nuevo_usuario = User.objects.create_user(
                    username=username, 
                    password=password, 
                    email=email
                )
                
                # B. Asignar Grupo
                group = Group.objects.get(name='cliente')
                nuevo_usuario.groups.add(group)

                # C. Crear el Cliente y ENLAZARLO
                Cliente.objects.create(
                    user=nuevo_usuario,   # <--- AQUÍ OCURRE EL ENLACE con el Usuario
                    documento=cedula,     # Aquí guardas la cédula
                    nombre_cliente=nombre,
                    apellido_cliente=apellido,
                    direccion=direccion,
                    telefono_cliente=telefono,
                    email=email
                )
                
                # Limpieza de sesión
                if 'pending_email' in request.session:
                    del request.session['pending_email']

                return redirect('login')

        except Exception as e:
            # Si algo falla en la base de datos
            return render(request, 'core/crear_usuario.html', {'error': f'Error al crear usuario: {e}'})

    # GET request...
    context = {
        'email': request.session.get('pending_email', ''),
        'cart_count': len(request.session.get('cart', []))
    }
    return render(request, 'core/crear_usuario.html', context)

@login_required
@admin_only

def crear_Productoo(request):
    try:
        if request.method == 'POST':
            post_data = request.POST.copy()
            categoria_custom = post_data.get('categoria_custom')
            otra_categoria = post_data.get('otra_categoria')
            # Si seleccionó 'otros', crear la categoría si no existe y usarla
            if categoria_custom == 'otros' and otra_categoria:
                cat_obj, _ = Categoria.objects.get_or_create(
                    nombre_categoria=otra_categoria.strip(),
                    defaults={'descripcion_categoria': f'Categoría personalizada: {otra_categoria.strip()}'},
                )
                post_data['categoria'] = cat_obj.pk
            elif categoria_custom and categoria_custom != 'otros':
                post_data['categoria'] = categoria_custom
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
    
    # Variable para guardar el objeto categoría encontrado (si existe)
    categoria_obj = None

    # Base queryset: solo productos activos
    Productos = (
        Producto.objects
        .filter(status_producto=True)
        .select_related('categoria')
        .only(
            'id',
            'nombre_producto',
            'precio_venta',
            'descripcion',
            'imagen_producto',
            'categoria__nombre_categoria',
            'categoria_id',
        )
    )

    if categoria_param:
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
    try:
        if user and user.email:
            cliente = Cliente.objects.filter(email__iexact=user.email).first()
            if cliente:
                # soportar diferentes nombres de campo según la versión del modelo
                cedula = getattr(cliente, 'cedula_dni', None) or getattr(cliente, 'documento', '') or ''
                telefono = getattr(cliente, 'telefono_cliente', None) or getattr(cliente, 'telefono', '') or ''
    except Exception:
        cliente = None

    return render(request, 'core/perfil.html', {
        'user': user,
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
        'cart_count': len(request.session.get('cart', [])),
        'cliente': cliente,
        'cedula': cedula,
        'telefono': telefono,
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
    for p in Productos:
        p.cantidad_en_carrito = cantidades.get(p.pk, 0)
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

    try:
        tasa= obtener_tasa_cambio()
    except Exception:
        tasa = 'N/A'

    return render(request, 'core/carrito.html', {
        'Productos': Productos,
        'producto_compra': producto_compra,
        'show_purchase_only': show_purchase_only,
        'cart_count': len(carrito_validado),
        'user_groups': _user_groups(request.user),
        'valor_dolar':str(tasa),
        
    })





#NOTA: Las funciones add_to_cart y remove_from_cart manejan el carrito de compras en la sesión del usuario.
#DE MOMENTO NO AGREGANDO NI ELIMINANDO PRODUCTOS DEL CARRITO EN LA BASE DE DATOS.

def add_to_cart(request, product_id):
    cart = request.session.get('cart', [])
    
    cart.append(product_id)
    request.session['cart'] = cart
    request.session.modified = True

    return JsonResponse({'count': len(cart)})

@login_required
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', [])

    # Remove the product entirely from session cart, even if it appears multiple times.
    pid = str(product_id)
    cart = [item for item in cart if str(item) != pid]
    request.session['cart'] = cart
    request.session.modified = True
    return redirect('carrito')


def logout_view(request):
    """Log out the current user and redirect to the login page."""
    try:
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
        .exclude(documento__isnull=True)
        .exclude(documento__exact='')
        .values('documento', 'nombre_cliente', 'apellido_cliente', 'direccion', 'telefono_cliente')
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
                cliente_datos = Cliente.objects.filter(documento=cliente_doc).first() 

            # Crear la Nota de Entrega
            nota = Nota_Entrega.objects.create(
                cliente=cliente_datos,
                estado_pago='APROBADO',
                fecha=timezone.now(),
                total=0.0,
                bcv=valor_bcv,
                fecha_revision=timezone.now(),
                revisado_por_id=request.user.pk,
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
    productos = (
        Producto.objects
        .select_related('categoria')
        .only(
            'id',
            'nombre_producto',
            'descripcion',
            'precio_venta',
            'cantidad_disponible',
            'status_producto',
            'categoria_id',
            'categoria__nombre_categoria',
            'imagen_producto',
        )
        .order_by('nombre_producto')
    )
    # Paginación: 10 productos por página
    paginator = Paginator(productos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for p in page_obj.object_list:
        p.img_url = _safe_img_url(p)
        p.status_producto = (p.cantidad_disponible or 0) > 0

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
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user)
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

    return render(request, 'core/historial_compras.html', {
        'salidas': notas,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True))
    })


@login_required

def comprar_producto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
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
                nota = Nota_Entrega.objects.create(
                    cliente=cliente_obj,
                    estado_pago='PENDIENTE',
                    fecha=timezone.now()
                )
                carrito_item = CarritoDeCompras.objects.create(Nota_Entrega=nota, Producto = producto, cantidad=cantidad, status_carrito=True, precio_unitario=producto.precio_venta
                ) 
                nota.carrito_de_compras = carrito_item
                nota.save()

                # Restar inventario
                cantidad_anterior = producto.cantidad_disponible or 0
                producto.cantidad_disponible = max(0, cantidad_anterior - cantidad)
                producto.save()

                # Registrar en historial de inventario
                Historial_Inventario.objects.create(
                    producto=producto,
                    cantidad_anterior=cantidad_anterior,
                    cantidad_nueva=producto.cantidad_disponible or 0,
                    tipo_movimiento='venta',
                    motivo=f'Compra por usuario {request.user.username} (cantidad {cantidad})',
                    usuario_responsable=request.user.username
                )
                


            # Quitar el producto comprado del carrito en la sesión
            # Limpieza de sesión
            cart = request.session.get('cart', [])
            if producto.pk in cart:
                cart.remove(producto.pk)
                request.session['cart'] = cart
                request.session.modified = True

            messages.success(request, 'Nota de entrega generada exitosamente.')
            # Redirigir usando el ID de la nota (antes era salida_id)
            return redirect('pago_exitoso', salida_id=nota.pk)
        
        except Exception as e:
            messages.error(request, f'Error al procesar la compra: {e}')
            return redirect('comprar_producto', producto_id=producto_id)

    # If requested as a partial (AJAX), return only the purchase form partial
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
    nota = get_object_or_404(Nota_Entrega, pk=nota_id)
    # Intentar recuperar items del carrito si existen
    items = nota.detalles.all().select_related('Producto')

    return render(request, 'core/pago_exitoso.html', {
        'salida': nota,  
        'items': items,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True))
    })


@admin_only
def aprobar_pagos(request):
    if request.method == 'POST':
        salida_id = request.POST.get('salida_id')
        accion = (request.POST.get('accion') or '').strip().lower()
        salida = get_object_or_404(Nota_Entrega, pk=salida_id, comprobante_pago__isnull=False)

        if salida.estado_pago != "PENDIENTE":
            print("asda")
            messages.info(request, 'Este pago ya fue revisado.')
            return redirect('aprobar_pagos')

        if accion == 'aprobar':
            salida.estado_pago = "APROBADO"
            messages.success(request, f'Pago #{salida.pk} aprobado correctamente.')
        elif accion == 'rechazar':
            salida.estado_pago = "RECHAZADO"
            messages.warning(request, f'Pago #{salida.pk} marcado como rechazado.')
        else:
            messages.error(request, 'Acción no válida.')
            return redirect('aprobar_pagos')

        salida.revisado_por = request.user
        salida.fecha_revision = timezone.now()
        salida.save(update_fields=['estado_pago', 'revisado_por', 'fecha_revision'])
        return redirect('aprobar_pagos')

    try:
        salidas = (
            Nota_Entrega.objects
            .filter(comprobante_pago__isnull=False, estado_pago='PENDIENTE')
            .select_related('cliente', 'cliente__user', 'revisado_por')
            .prefetch_related('detalles__Producto')
            .order_by('-fecha', '-id')
        )
        total_pendientes = salidas.count()
    except Exception as e:
        logger.error(f'Error al cargar pagos pendientes: {e}', exc_info=True)
        salidas = []
        total_pendientes = 0

    return render(request, 'core/aprobar_pagos.html', {
        'salidas': salidas,
        'total_pendientes': total_pendientes,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': _user_groups(request.user),
    })


@login_required
def detalles_salida(request, salida_id):
    """Mostrar todos los productos incluidos en una Nota de Entrega (antes Salida) específica."""
    nota = get_object_or_404(Nota_Entrega, pk=salida_id)
    

    items = (
        nota.detalles  # Esto accede a todos los CarritoDeCompras asociados a esta Nota
        .all()
        .select_related('Producto')  # Optimización de base de datos
    )
    
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

    payment_proof = request.FILES.get('payment_proof')
    saved_proof_path = None
    if payment_proof:
        content_type = (payment_proof.content_type or '').lower()
        if not content_type.startswith('image/'):
            messages.error(request, 'El comprobante debe ser una imagen valida.')
            return redirect('carrito')
        
        if payment_proof.size > (5 * 1024 * 1024):
            messages.error(request, 'El comprobante supera el tamano maximo de 5 MB.')
            return redirect('carrito')

        _, ext = os.path.splitext(payment_proof.name or '')
        ext = (ext or '.jpg').lower()
        proof_name = f"payment_proofs/{request.user.pk}_{timezone.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
        try:
            saved_proof_path = default_storage.save(proof_name, payment_proof)
        except Exception:
            messages.error(request, 'No se pudo guardar la imagen del comprobante.')
            return redirect('carrito')

    productos = Producto.objects.filter(pk__in=cart)

    try:
        with transaction.atomic():
            # PASO 1: Obtener cliente y crear la cabecera (Nota_Entrega)
            cliente_obj = getattr(request.user, 'cliente', None)
            nota = Nota_Entrega.objects.create(
                cliente=cliente_obj,
                estado_pago='PENDIENTE',
                fecha=timezone.now(),
                total=0.0
            )
            logger.info(f'Nota_Entrega creada: {nota.pk} para usuario {request.user.username}')
            
            total_acumulado = 0.0

            # PASO 2: Procesar cada producto del carrito
            for p in productos:
                qty = request.POST.get(f'cantidad_{p.pk}') or request.POST.get(f'qty_{p.pk}') or 1
                try:
                    cantidad = int(qty)
                except:
                    cantidad = 1

                available = p.cantidad_disponible or 0
                if cantidad <= 0 or cantidad > available:
                    messages.error(request, f'Cantidad no disponible para {p.nombre}.')
                    raise ValueError('stock insuficiente')

                subtotal = float(p.precio_venta or 0) * cantidad
                
                # PASO 3: Crear el detalle en CarritoDeCompras vinculado a la Nota
                CarritoDeCompras.objects.create(
                    Nota_Entrega=nota,
                    Producto=p,
                    Cantidad=cantidad,
                    precio_unitario=p.precio_venta,
                    status_carrito=True
                )

                # PASO 4: Actualizar inventario e historial
                cant_anterior = p.cantidad_disponible or 0
                p.cantidad_disponible = max(0, cant_anterior - cantidad)
                p.save()

                Historial_Inventario.objects.create(
                    producto=p,
                    cantidad_anterior=cant_anterior,
                    cantidad_nueva=p.cantidad_disponible,
                    tipo_movimiento='venta',
                    motivo=f'Venta múltiple - Nota #{nota.id}',
                    usuario_responsable=request.user.username
                )

                total_acumulado += subtotal

            # PASO 5: Actualizar el total final de la Nota
            nota.total = total_acumulado
            if saved_proof_path:
                nota.comprobante_pago = saved_proof_path
                logger.info(f'Comprobante asignado a nota {nota.pk}: {saved_proof_path}')
            nota.save()
            logger.info(f'Nota {nota.pk} guardada con total {total_acumulado}')

            request.session['cart'] = []

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

    productos = Producto.objects.filter(pk__in=cart)
    items = []
    total = 0.0
    # recoger cantidades desde request.POST
    for p in productos:
        qty = request.POST.get(f'cantidad_{p.pk}') or request.POST.get(f'qty_{p.pk}') or request.POST.get(str(p.pk)) or 1
        try:
            cantidad = int(qty)
        except Exception:
            cantidad = 1
        subtotal = float(p.precio_venta or 0) * cantidad
        items.append({'producto': p, 'cantidad': cantidad, 'subtotal': subtotal})
        total += subtotal

    return render(request, 'core/pago_movil.html', {
        'items': items,
        'total': total,
        'post': request.POST,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True))
    })




@login_required
def comprar_producto_ajax(request, producto_id):
    """Procesa la compra de un solo producto vía AJAX usando Nota_Entrega."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

    producto = get_object_or_404(Producto, pk=producto_id)
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
            
            nota = Nota_Entrega.objects.create(
                cliente=cliente_obj,
                estado_pago='PENDIENTE',
                total=subtotal,
                fecha=timezone.now()
            )

            # PASO 2: Crear el detalle en CarritoDeCompras vinculado a la Nota
            item_carrito = CarritoDeCompras.objects.create(
                Nota_Entrega=nota,
                Producto=producto,
                Cantidad=cantidad,
                precio_unitario=producto.precio_venta,
                status_carrito=True
            )

            # PASO 3: Actualizar inventario
            cantidad_anterior = producto.cantidad_disponible or 0
            producto.cantidad_disponible = max(0, cantidad_anterior - cantidad)
            producto.save()

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
                    request.session.modified = True
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
    except Exception:
        request.session.pop('cart', None)
    messages.success(request, 'Se han eliminado todos los productos del carrito.')
    return redirect('carrito')

@login_required
@admin_only
def eliminar_producto(request, producto_id):
    if request.method == 'POST':
        try:
            producto = get_object_or_404(Producto, pk=producto_id)
            nombre_producto = producto.nombre_producto
            producto.delete()
            # Ensure current session cart is cleaned (remove any occurrence of this product id)
            try:
                cart = request.session.get('cart', [])
                if producto_id in cart:
                    cart = [pid for pid in cart if pid != producto_id]
                    request.session['cart'] = cart
            except Exception:
                pass
            messages.success(request, f'El producto "{nombre_producto}" ha sido eliminado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar el producto: {str(e)}')
    
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
            # Usamos '0' como fallback si viene vacío para evitar crash en int()
            nueva_cantidad = int(request.POST.get('cantidad_disponible') or 0)

            # Lo mismo para el precio
            precio_raw = request.POST.get('precio_venta')
            nuevo_precio = float(precio_raw) if precio_raw else producto.precio_venta

        except ValueError:
            messages.error(request, 'Error: La cantidad o el precio deben ser números válidos.')
            return redirect('inventario')

        # Pre-validate: require a non-empty motivo if any editable field changes
        motivo = (request.POST.get('motivoAjuste') or '').strip()

        # Determine posted values for comparison
        posted_nombre = (request.POST.get('nombre_producto') or '').strip()
        posted_desc = (request.POST.get('descripcion') or '').strip()
        posted_precio = nuevo_precio
        posted_cantidad = nueva_cantidad
        posted_status = (request.POST.get('status_producto') == 'true')
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
        # compare numeric with tolerance for floats
        try:
            if float(posted_precio) != float(producto.precio_venta or 0):
                changed = True
                changed_non_image = True
        except Exception:
            pass
        try:
            if int(posted_cantidad) != int(producto.cantidad_disponible or 0):
                changed = True
                changed_non_image = True
        except Exception:
            pass
        if bool(posted_status) != bool(producto.status_producto):
            changed = True
            changed_non_image = True
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

                producto.cantidad_disponible = nueva_cantidad

                # Manejo correcto de checkbox (si no está marcado, no envía 'true', envía None)

                producto.status_producto = request.POST.get('status_producto') == 'true'

                # Lógica de categoría
                if categoria_id:
                    if categoria_id.isdigit(): # Validación extra
                        producto.categoria_id = int(categoria_id) # Asignación directa por ID es más rápida

                if request.FILES.get('imagen_producto'):
                    producto.imagen_producto = request.FILES['imagen_producto']

                # GUARDAMOS EL PRODUCTO PRIMERO
                producto.save()

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
            messages.error(request, f'Error al actualizar el producto: {str(e)}')

    return redirect('inventario')

@login_required
@admin_only
def todos_clientes(request):
    clientes_qs = (
        Cliente.objects
        .only('id', 'nombre_cliente', 'apellido_cliente', 'documento', 'rif_empresarial', 'telefono_cliente', 'email')
        .order_by('nombre_cliente')
    )
    paginator = Paginator(clientes_qs, 25)
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
        'user_groups': _user_groups(request.user)
    })

@login_required
@admin_only
def agregar_marca(request):
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        marca = request.POST.get('marca_producto', '').strip()
        
        if producto_id and marca:
            try:
                producto = Producto.objects.get(pk=producto_id)
                marca_anterior = (producto.marca_producto or '').strip()
                producto.marca_producto = marca
                producto.save()
                if marca_anterior and marca_anterior.lower() != marca.lower():
                    messages.success(
                        request,
                        f'Marca actualizada en "{producto.nombre_producto}": "{marca_anterior}" -> "{marca}".'
                    )
                elif marca_anterior and marca_anterior.lower() == marca.lower():
                    messages.success(
                        request,
                        f'La marca de "{producto.nombre_producto}" ya estaba en "{marca}".'
                    )
                else:
                    messages.success(request, f'Marca "{marca}" agregada al producto "{producto.nombre_producto}".')
            except Producto.DoesNotExist:
                messages.error(request, 'Producto no encontrado.')
            except Exception as e:
                messages.error(request, f'Error al agregar la marca: {str(e)}')
        else:
            messages.error(request, 'Debes seleccionar un producto y proporcionar una marca.')
        
        return redirect('agregar_marca')
    
    # Obtener todos los productos para permitir seleccionar cualquiera
    productos = Producto.objects.all().order_by('nombre_producto')

    # Mantener a la vista los no marcados para información, pero no bloquea
    productos_sin_marca = productos.filter(Q(marca_producto__isnull=True) | Q(marca_producto=''))

    return render(request, 'core/agregar_marca.html', {
        'productos': productos,
        'productos_sin_marca': productos_sin_marca,
        'cart_count': len(request.session.get('cart', [])),
        'user_groups': list(request.user.groups.values_list('name', flat=True))
    })