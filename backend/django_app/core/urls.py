from django.urls import path
from django.views.generic import RedirectView
from . import views
from . import views_inventario_api
from .views import cobrar_caja, descargar_factura_ne
urlpatterns = [
    path('', views.home, name='home'),
    path('home/', views.home, name='home_page'),
    path('login/', views.login_view, name='login'),
    path('login', views.login_post, name='login_post'),
    path('verificar-correo/', views.verificar_correo, name='verificar_correo'),
    path('recuperar-contrasena/', views.recuperar_contrasena, name='recuperar_contrasena'),
    path('cliente/registrar/', views.crear_cliente, name='registrar_cliente'),
    path('cliente/crear_usuario/', views.crear_usuario, name='crear_usuario'),
    path('producto/registrar/', views.crear_Productoo, name='registrar_producto'),
    path('producto/registrar-debug/', views.crear_Productoo_debug, name='registrar_producto_debug'),
    # Compatibilidad antigua
    path('registrar/', RedirectView.as_view(pattern_name='registrar_producto', permanent=False)),
    path('catalogo/', views.catalog, name='catalog'),
    path('perfil/', views.perfil, name='perfil'),
    path('carrito/', views.carrito, name='carrito'),
    path('caja/', views.caja, name='caja'),
    path('caja/cobrar/', views.cobrar_caja, name='cobrar_caja'),
    path('comprar_carrito/', views.comprar_carrito, name='comprar_carrito'),
    path('pago_movil/', views.pago_movil, name='pago_movil'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('clear_cart/', views.clear_cart, name='clear_cart'),
    path('remove_from_cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('logout/', views.logout_view, name='logout'),
    path('inventario/', views.inventario, name='inventario'),
    path('inventario/historial/', views.historial_inventario, name='historial_inventario'),
    path('producto/<int:producto_id>/', views.producto_detalle, name='producto_detalle'),
    path('producto/<int:producto_id>/camisas/', views.camisas_shein, name='camisas_shein'),
    path('producto/<int:producto_id>/comprar/', views.comprar_producto, name='comprar_producto'),
    path('producto/<int:producto_id>/comprar_ajax/', views.comprar_producto_ajax, name='comprar_producto_ajax'),
    path('producto/<int:producto_id>/detalles_compra/', views.detalles_compra_producto, name='detalles_compra_producto'),
    path('historial/', views.historial_compras, name='historial_compras'),
    path('producto/<int:producto_id>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('producto/<int:producto_id>/estado/', views.cambiar_estado_producto, name='cambiar_estado_producto'),
    path('producto/<int:producto_id>/ajustar/', views.ajustar_inventario, name='ajustar_inventario'),
    path('producto/<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),
    path('pedido/exitoso/<int:salida_id>/', views.pago_exitoso, name='pago_exitoso'),
    path('pedido/<int:salida_id>/detalles/', views.detalles_salida, name='detalles_salida'),
    path('pagos/aprobar/', views.aprobar_pagos, name='aprobar_pagos'),
    path('pagos/sublimacion/', views.ordenes_sublimacion, name='ordenes_sublimacion'),
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/productos/csv/', views.descargar_reporte_productos, name='descargar_reporte_productos'),
    path('reportes/producto/<int:producto_id>/pdf/', views.descargar_reporte_producto, name='descargar_reporte_producto'),
    path('reportes/clientes/pdf/', views.descargar_reporte_clientes, name='descargar_reporte_clientes'),
    path('reportes/reembolsos/pdf/', views.descargar_reporte_reembolsos, name='descargar_reporte_reembolsos'),
    path('reportes/carrito/pdf/', views.descargar_reporte_carrito, name='descargar_reporte_carrito'),
    # Solicitudes legacy/static que algunos templates/scripts aún utilizan
    path('home.html', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('index.html', RedirectView.as_view(pattern_name='login', permanent=False)),
    # Compatibilidad heredada: algunos redirects de auth usan /accounts/login/
    path('accounts/login/', RedirectView.as_view(pattern_name='login', permanent=False, query_string=True)),
    # Compatibilidad: URL heredada usada por algunos enlaces/scripts antiguos
    path('comprar_producto/<int:producto_id>/', RedirectView.as_view(url='/producto/%(producto_id)s/comprar/', permanent=False)),
    path('todos_clientes/', views.todos_clientes, name='todos_clientes'),
    path('todos_clientes/<int:cliente_id>/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),
    path('agregar_marca/', views.agregar_marca, name='agregar_marca'),
    path('factura/descargar/<int:pk>/', descargar_factura_ne, name='descargar_factura_ne'),
    # Nueva ruta para ajuste masivo de inventario
    path('ajustar_inventario/', views.ajustar_inventario_masivo, name='ajustar_inventario_masivo'),
    # API para ajuste de stock
    path('api/ajustar_stock/', views_inventario_api.ajustar_stock_producto, name='api_ajustar_stock'),
    path('cobrar-caja/', cobrar_caja, name='cobrar_caja'),
    
]