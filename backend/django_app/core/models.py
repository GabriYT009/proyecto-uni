from django.db import models
from django.db import models
from django.contrib.auth.models import User as Usuario

# ==========================================
# 1. Tablas Maestras


class TipoCliente(models.Model):
    tipo_documento = models.CharField(max_length=45)

    class Meta:
        verbose_name = 'Tipo de Cliente'
        verbose_name_plural = 'Tipos de Clientes'

    def __str__(self):
        return self.tipo_documento


class Rol(models.Model):
    nombre_rol = models.CharField(max_length=45)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre_rol


class Empleado(models.Model):
    nombre = models.CharField(max_length=45, blank=True, null=True)
    apellido = models.CharField(max_length=45, blank=True, null=True)
    cedula_dni = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Bcv(models.Model):
    precio_actual = models.FloatField()
    fecha = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Tasa BCV'
        verbose_name_plural = 'Tasas BCV'


class MetodoPago(models.Model):
    nombre_metodo_pago = models.CharField(max_length=45, blank=True, null=True)
    status_pago = models.BooleanField(default=True) # TINYINT(1)

    def __str__(self):
        return self.nombre_metodo_pago


class Categoria(models.Model):
    # Coincide con tu modelo anterior pero agregando los campos del SQL
    nombre_categoria = models.CharField('Nombre', max_length=45, blank=True, null=True)
    descripcion_categoria = models.CharField('Descripción', max_length=45, blank=True, null=True)
    
    # Campos nuevos según SQL
    rif_proveedor = models.CharField(max_length=45, blank=True, null=True)
    telefono_proveedor = models.CharField(max_length=45, blank=True, null=True)
    direccion_proveedor = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre_categoria or "Categoría sin nombre"


class Suministro(models.Model):
    nombre_suministro = models.CharField(max_length=100, blank=True, null=True)
    unidad_medida = models.CharField(max_length=20, blank=True, null=True)
    cantidad_stock = models.FloatField(blank=True, null=True)
    stock_minimo = models.FloatField(blank=True, null=True)
    precio_costo = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.nombre_suministro


class Servicio(models.Model):
    nombre_servicio = models.CharField(max_length=45, blank=True, null=True)
    precio_unidad = models.FloatField(blank=True, null=True)
    sub_total_servicio = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.nombre_servicio


# ==========================================
# 2. Tablas con dependencias intermedias


class Cliente(models.Model):
    # En el SQL, 'tipo_cliente' es una FK, no un Choice estático
    tipo_cliente = models.ForeignKey(TipoCliente, on_delete=models.SET_NULL, null=True, blank=True)
    
    documento = models.CharField(max_length=45, blank=True, null=True)
    rif_empresarial = models.CharField(max_length=45, blank=True, null=True)
    nombre_cliente = models.CharField(max_length=45, blank=True, null=True)
    apellido_cliente = models.CharField(max_length=45, blank=True, null=True)
    direccion = models.CharField(max_length=100, blank=True, null=True)
    telefono_cliente = models.CharField(max_length=15, blank=True, null=True)
    email = models.CharField(max_length=45, blank=True, null=True)
    user = models.OneToOneField(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f"{self.nombre_cliente} {self.apellido_cliente}"
    
class Marca_producto(models.Model):
    nombre_marca = models.CharField(max_length=45, blank=True, null=True, unique=True)
 
    class Meta:
        verbose_name = 'Marca de Producto'
        verbose_name_plural = 'Marcas de Productos'

    def __str__(self):
        return self.nombre_marca

class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, null=True, blank=True)
    nombre_producto = models.CharField(max_length=45, blank=True, null=True)
    descripcion = models.CharField(max_length=45, blank=True, null=True)
    marca_producto = models.ForeignKey(Marca_producto, on_delete=models.SET_NULL, null=True, blank=True)
    max_producto = models.IntegerField(blank=True, null=True)
    precio_venta = models.FloatField(blank=True, null=True)
    status_producto = models.BooleanField(default=True) # TINYINT(1)
    cantidad_disponible = models.IntegerField(blank=True, null=True)
    imagen_producto = models.ImageField(upload_to='products/', max_length=100, blank=True, null=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return self.nombre_producto

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Copiar la imagen a static/product-images/ si existe
        if self.imagen_producto and self.imagen_producto.name:
            import shutil, os
            from django.conf import settings
            # Algunos storage remotos (R2/S3/Cloudinary) no soportan `.path`.
            try:
                media_path = self.imagen_producto.path
            except Exception:
                return

            # Nombre base del archivo
            image_basename = os.path.basename(media_path)
            # Destino en static/product-images/
            static_dir = os.path.join(settings.FRONTEND_DIR, 'static', 'product-images')
            os.makedirs(static_dir, exist_ok=True)
            static_path = os.path.join(static_dir, image_basename)
            try:
                if not os.path.exists(static_path):
                    shutil.copy2(media_path, static_path)
            except Exception:
                # No interrumpir el guardado si falla la copia
                pass


# ==========================================
# 3. Tablas de Operación y Transacciones


class CarritoDeCompras(models.Model):
    Nota_Entrega = models.ForeignKey('Nota_Entrega', related_name='detalles', on_delete=models.CASCADE)
    Producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    Cantidad=models.PositiveIntegerField(default=1)
    talla = models.CharField(max_length=10, blank=True, null=True)
    status_carrito = models.BooleanField(default=False)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.Cantidad} x {self.Producto.nombre} (Nota de Entrega {self.Nota_Entrega.id})"

#paso 1
class Nota_Entrega(models.Model):

    ESTADO_PAGO = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADO', 'Aprobado'),
        ('RECHAZADO', 'Rechazado'),
    ]
    Tipo_pago = [
        ('EFECTIVO', 'Efectivo'),
        ('PAGO MOVIL', 'Pago Móvil'),
        ('TARJETA', 'Tarjeta')]
    
    bcv = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    carrito_de_compras = models.ForeignKey(CarritoDeCompras, on_delete=models.SET_NULL, null=True, blank=True)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True)
    comprobante_pago = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)

    estado_pago = models.CharField(max_length=20, choices=ESTADO_PAGO, default='PENDIENTE')
    revisado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='Nota_Entrega_revisadas',
    )

    fecha_revision = models.DateTimeField(blank=True, null=True)
    tipo_pago = models.CharField(max_length=20, choices=Tipo_pago, blank=True, null=True)
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)
    total = models.FloatField(blank=True, null=True)
    fecha = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Nota_Entrega (Venta)'
        verbose_name_plural = 'Nota_Entrega'

#paso 2

class OrdenDeDespacho(models.Model):
    # Esto parece funcionar como un "CartItem" o detalle del carrito

    carrito_de_compras = models.ForeignKey(CarritoDeCompras, on_delete=models.CASCADE, null=True, blank=True)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    
    cantidad_item = models.IntegerField(blank=True, null=True)
    sub_total_item = models.FloatField(blank=True, null=True)
    estado_disponibilidad = models.BooleanField(default=True)


class ServicioSublimado(models.Model):
    sub_total_sublimado = models.FloatField(blank=True, null=True)
    precio_unidad = models.FloatField(blank=True, null=True)
    cantidad = models.IntegerField(blank=True, null=True)
    fecha_de_pedido = models.DateField(blank=True, null=True)
    fecha_de_entrega = models.DateField(blank=True, null=True)


class DetalleServicio(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    servicio_sublimado = models.ForeignKey(ServicioSublimado, on_delete=models.SET_NULL, null=True, blank=True)
    carrito_de_compras = models.ForeignKey(CarritoDeCompras, on_delete=models.CASCADE, null=True, blank=True)
    
    sub_total_servicio = models.FloatField(blank=True, null=True)
 

class SolicitudSublimacion(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('VINCULADA', 'Vinculada'),
        ('RECHAZADA', 'Rechazada'),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='solicitudes_sublimacion')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='solicitudes_sublimacion')
    carrito_de_compras = models.ForeignKey(CarritoDeCompras, on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_sublimacion')
    nota_entrega = models.ForeignKey('Nota_Entrega', on_delete=models.SET_NULL, null=True, blank=True, related_name='solicitudes_sublimacion')
    talla = models.CharField(max_length=10, blank=True, null=True)
    comentario = models.TextField(blank=True, null=True)
    imagen_sublimacion = models.ImageField(upload_to='sublimaciones/', blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Sublimacion {self.producto_id} - {self.usuario_id}'


# ==========================================
# 4. Tablas de Relación de Suministros


class ServicioSuministro(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    suministro = models.ForeignKey(Suministro, on_delete=models.CASCADE)
    cantidad_usada_por_unidad = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name = 'Insumo por Servicio'


class SublimadoConsumoSuministro(models.Model):
    servicio_sublimado = models.ForeignKey(ServicioSublimado, on_delete=models.CASCADE)
    suministro = models.ForeignKey(Suministro, on_delete=models.CASCADE)
    cantidad_consumida = models.FloatField(blank=True, null=True)

class Historial_Inventario(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True, related_name='historial')
    cantidad_anterior = models.IntegerField(default=0)
    cantidad_nueva = models.IntegerField(default=0)
    tipo_movimiento = models.CharField(max_length=45) 
    fecha_ajuste = models.DateTimeField(auto_now_add=True) # Se llena solo
    motivo = models.CharField(max_length=255)
    usuario_responsable = models.TextField()

    class Meta:
        verbose_name = 'Historial de Inventario'
        verbose_name_plural = 'Historiales de Inventario'





















# class Category(models.Model):
#     name = models.CharField('Nombre', max_length=100)
#     slug = models.SlugField(unique=True)
#     description = models.TextField('Descripción', blank=True)

#     class Meta:
#         verbose_name = 'Categoría'
#         verbose_name_plural = 'Categorías'
#         app_label = 'core'

#     def __str__(self):
#         return self.name


# class Product(models.Model):
# 	title = models.CharField('Nombre de producto', max_length=200)
# 	price = models.CharField('Precio', max_length=50, blank=True)
# 	img = models.ImageField('Imagen', blank=True, upload_to='products/')
# 	desc = models.TextField('Descripción', blank=True)
# 	category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', blank=True, null=True)

# 	class Meta:
# 		verbose_name = 'Producto'
# 		verbose_name_plural = 'Productos'
# 		app_label = 'core'

# 	def __str__(self):
# 		return self.title


# class Cliente(models.Model):
# 	TIPO_CHOICES = (
# 		('1', 'Persona Natural'),
# 		('2', 'Persona Jurídica'),
# 	)

# 	id_tipo_cliente = models.CharField('Tipo de cliente', max_length=1, choices=TIPO_CHOICES)
# 	nombre_cliente = models.CharField('Nombre', max_length=45)
# 	apellido_cliente = models.CharField('Apellido', max_length=45, blank=True)
# 	direccion = models.CharField('Dirección', max_length=255, blank=True)
# 	telefono_cliente = models.CharField('Teléfono', max_length=11, blank=True)
# 	email = models.EmailField('Email')

# 	# Identificación natural
# 	cedula_dni = models.CharField('Cédula / DNI', max_length=11, blank=True)

# 	# Identificación jurídica
# 	rif_empresa = models.CharField('RIF', max_length=22, blank=True)
# 	nombre_empresa = models.CharField('Nombre empresa', max_length=255, blank=True)
# 	cedula_dni_representante = models.CharField('Cédula representante', max_length=11, blank=True)

# 	created_at = models.DateTimeField('Creado', auto_now_add=True)

# 	class Meta:
# 		verbose_name = 'Cliente'
# 		verbose_name_plural = 'Clientes'
# 		app_label = 'core'

# 	def __str__(self):
# 		return f"{self.nombre_cliente} {self.apellido_cliente or ''} <{self.email}>"
