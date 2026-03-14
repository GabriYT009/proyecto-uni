from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home', views.home, name='home'),
    path('login', views.login_post, name='login_post'),
    path('cliente/registrar/', views.crear_cliente, name='registrar_cliente'),
    path('cliente/crear_usuario/', views.crear_usuario, name='crear_usuario'),
    path('producto/registrar/', views.crear_Productoo, name='registrar_producto'),
    # Compatibilidad antigua
    path('registrar/', RedirectView.as_view(pattern_name='registrar_producto', permanent=False)),
    path('catalogo/', views.catalog, name='catalog'),
    path('perfil/', views.perfil, name='perfil'),
    path('carrito/', views.carrito, name='carrito'),
    path('caja/', views.caja, name='caja'),
    path('comprar_carrito/', views.comprar_carrito, name='comprar_carrito'),
    path('pago_movil/', views.pago_movil, name='pago_movil'),
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('clear_cart/', views.clear_cart, name='clear_cart'),
    path('remove_from_cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('logout/', views.logout_view, name='logout'),
    path('inventario/', views.inventario, name='inventario'),
    path('producto/<int:producto_id>/', views.producto_detalle, name='producto_detalle'),
    path('producto/<int:producto_id>/comprar/', views.comprar_producto, name='comprar_producto'),
    path('producto/<int:producto_id>/comprar_ajax/', views.comprar_producto_ajax, name='comprar_producto_ajax'),
    path('producto/<int:producto_id>/detalles_compra/', views.detalles_compra_producto, name='detalles_compra_producto'),
    path('historial/', views.historial_compras, name='historial_compras'),
    path('producto/<int:producto_id>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('producto/<int:producto_id>/ajustar/', views.ajustar_inventario, name='ajustar_inventario'),
    path('producto/<int:producto_id>/editar/', views.editar_producto, name='editar_producto'),
    path('pedido/exitoso/<int:salida_id>/', views.pago_exitoso, name='pago_exitoso'),
    path('pedido/<int:salida_id>/detalles/', views.detalles_salida, name='detalles_salida'),
    # legacy/static file requests that some templates/scripts still use
    path('home.html', RedirectView.as_view(pattern_name='home', permanent=False)),
    path('index.html', RedirectView.as_view(pattern_name='login', permanent=False)),
    # legacy compatibility: some auth redirects use /accounts/login/
    path('accounts/login/', RedirectView.as_view(pattern_name='login', permanent=False, query_string=True)),
    # compatibility: legacy URL used by some older links/scripts
    path('comprar_producto/<int:producto_id>/', RedirectView.as_view(url='/producto/%(producto_id)s/comprar/', permanent=False)),
    path('todos_clientes/', views.todos_clientes, name='todos_clientes'),
    path('agregar_marca/', views.agregar_marca, name='agregar_marca'),
    
]