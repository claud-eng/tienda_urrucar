from . import views  # Importa las vistas definidas en el directorio actual (directorio donde se encuentra este archivo)
from .views import generar_comprobante, generar_comprobante_online
from django.urls import include, path  # Importa path para definir rutas de URL e include para incluir otras configuraciones de URL

urlpatterns = [
    # Ruta para gestionar el inventario siendo administrador
    path('gestionar_inventario', views.gestionar_inventario, name='gestionar_inventario'),
    # Rutas para los productos
    path('listar_productos', views.listar_productos, name="listar_productos"),
    path('agregar_producto', views.agregar_producto, name="agregar_producto"),
    path('editar_producto/<int:producto_id>', views.editar_producto, name="editar_producto"),
    path('borrar_producto/<int:producto_id>', views.borrar_producto, name="borrar_producto"),
    path('confirmar-borrar-producto/<int:producto_id>/', views.confirmar_borrar_producto, name='confirmar_borrar_producto'),
    # Rutas para los servicios
    path('listar_servicios', views.listar_servicios, name="listar_servicios"),
    path('agregar_servicio', views.agregar_servicio, name="agregar_servicio"),
    path('editar_servicio/<int:servicio_id>', views.editar_servicio, name="editar_servicio"),
    path('borrar_servicio/<int:servicio_id>', views.borrar_servicio, name="borrar_servicio"),
    path('confirmar-borrar-servicio/<int:servicio_id>/', views.confirmar_borrar_servicio, name='confirmar_borrar_servicio'),
    path('catalogo_productos', views.catalogo_productos, name='catalogo_productos'), 
    path('ver_detalles_producto/<int:producto_id>/', views.ver_detalles_producto, name='ver_detalles_producto'),   
    path('catalogo_servicios', views.catalogo_servicios, name='catalogo_servicios'),   
    # Agregar un producto al carrito
    path('agregar_al_carrito/producto/<int:id>/', views.agregar_al_carrito, {'tipo': 'producto'}, name='agregar_producto_al_carrito'),
    # Agregar un servicio al carrito
    path('agregar_al_carrito/servicio/<int:id>/', views.agregar_al_carrito, {'tipo': 'servicio'}, name='agregar_servicio_al_carrito'), 
    path('carrito/', views.carrito, name='carrito'),  # Agrega esta línea para la vista 'carrito'
    path('realizar_compra/', views.realizar_compra, name='realizar_compra'),
    path('eliminar_del_carrito/<int:item_id>/', views.eliminar_del_carrito, name='eliminar_del_carrito'),
    path('vaciar_carrito/', views.vaciar_carrito, name='vaciar_carrito'),
    path('aumentar_cantidad/<int:item_id>/', views.aumentar_cantidad, name='aumentar_cantidad'),
    path('disminuir_cantidad/<int:item_id>/', views.disminuir_cantidad, name='disminuir_cantidad'),
    path('iniciar_transaccion/', views.iniciar_transaccion, name='iniciar_transaccion'),
    path('transaccion_finalizada/', views.transaccion_finalizada, name='transaccion_finalizada'),
    path('listar_ventas_online', views.listar_ventas_online, name='listar_ventas_online'),   
    path('ventas_online/comprobante/<str:numero_orden>/', generar_comprobante_online, name='generar_comprobante_online'),
    path('agregar_venta', views.agregar_venta, name='agregar_venta'),
    path('listar_ventas', views.listar_ventas, name='listar_ventas'),
    path('ventas/comprobante/<int:id_venta>/', generar_comprobante, name='generar_comprobante'),
    path('gestionar_transacciones', views.gestionar_transacciones, name='gestionar_transacciones'),
    path('reportes_ventas', views.reportes_ventas, name='reportes_ventas'),
    path('exportar-pdf/', views.exportar_pdf, name='exportar_pdf'),
]