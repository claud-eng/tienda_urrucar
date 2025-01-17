from django.urls import include, path  # Importa 'path' para definir rutas de URL y 'include' para incluir otras configuraciones de URL.
from . import views  # Importa las vistas definidas en el directorio actual.
from .carrito import *  # Importa todas las funciones relacionadas con la gestión del carrito de compras.
from .functions import descargar_comprobante_pago # Importa una función para descargar un comprobante de venta en formato pdf.
from .webpay import iniciar_transaccion, transaccion_finalizada  # Importa funciones para iniciar y finalizar transacciones con Webpay.

urlpatterns = [
    path('agregar_al_carrito/producto/<int:id>/', agregar_al_carrito, {'tipo': 'producto'}, name='agregar_producto_al_carrito'),  # Agregar un producto al carrito
    path('agregar_al_carrito/servicio/<int:id>/', agregar_al_carrito, {'tipo': 'servicio'}, name='agregar_servicio_al_carrito'),  # Agregar un servicio al carrito
    path('agregar_producto', views.agregar_producto, name="agregar_producto"),  # Ruta para agregar producto
    path('agregar_servicio', views.agregar_servicio, name="agregar_servicio"),  # Ruta para agregar servicio
    path('agregar_venta_manual', views.agregar_venta_manual, name='agregar_venta_manual'),  # Ruta para agregar venta
    path('aumentar_cantidad/<int:item_id>/', aumentar_cantidad, name='aumentar_cantidad'),  # Aumentar cantidad de un ítem en el carrito
    path('borrar_producto/<int:producto_id>', views.borrar_producto, name="borrar_producto"),  # Ruta para borrar producto
    path('borrar_servicio/<int:servicio_id>', views.borrar_servicio, name="borrar_servicio"),  # Ruta para borrar servicio
    path('carrito/', carrito, name='carrito'),  # Vista para ver el carrito
    path('catalogo_productos', views.catalogo_productos, name='catalogo_productos'),  # Vista de catálogo de productos
    path('catalogo_servicios', views.catalogo_servicios, name='catalogo_servicios'),  # Vista de catálogo de servicios
    path('confirmar-borrar-producto/<int:producto_id>/', views.confirmar_borrar_producto, name='confirmar_borrar_producto'),  # Confirmar borrado de producto
    path('confirmar-borrar-servicio/<int:servicio_id>/', views.confirmar_borrar_servicio, name='confirmar_borrar_servicio'),  # Confirmar borrado de servicio
    path('transaccion/descargar-comprobante/<str:tipo_venta>/<str:identificador>/', descargar_comprobante_pago, name='descargar_comprobante_pago'), # Descargar comprobante de pago en formato pdf
    path('disminuir_cantidad/<int:item_id>/', disminuir_cantidad, name='disminuir_cantidad'),  # Disminuir cantidad de un ítem en el carrito
    path('editar_producto/<int:producto_id>', views.editar_producto, name="editar_producto"),  # Editar un producto
    path('eliminar_imagen_adicional/<int:imagen_id>/', views.eliminar_imagen_adicional, name='eliminar_imagen_adicional'),
    path('editar_servicio/<int:servicio_id>', views.editar_servicio, name="editar_servicio"),  # Editar un servicio
    path('editar-venta-online/<int:venta_id>/', views.editar_venta_online, name='editar_venta_online'), # Editar una venta online
    path('eliminar_del_carrito/<int:item_id>/', eliminar_del_carrito, name='eliminar_del_carrito'),  # Eliminar ítem del carrito
    path('gestionar_inventario', views.gestionar_inventario, name='gestionar_inventario'),  # Gestionar inventario (administrador)
    path('gestionar_transacciones', views.gestionar_transacciones, name='gestionar_transacciones'),  # Gestionar transacciones
    path('iniciar_transaccion/', iniciar_transaccion, name='iniciar_transaccion'),  # Iniciar transacción de pago
    path('listar_productos', views.listar_productos, name="listar_productos"),  # Listar productos
    path('listar_servicios', views.listar_servicios, name="listar_servicios"),  # Listar servicios
    path('listar_ventas_manuales', views.listar_ventas_manuales, name='listar_ventas_manuales'),  # Listar ventas manuales
    path('listar_ventas_online', views.listar_ventas_online, name='listar_ventas_online'),  # Listar ventas online
    path('realizar_compra/', realizar_compra, name='realizar_compra'),  # Realizar compra
    path('reporte_ventas_manuales', views.reporte_ventas_manuales, name='reporte_ventas_manuales'),  # Reportes de ventas manuales
    path('reporte_ventas_online', views.reporte_ventas_online, name='reporte_ventas_online'),  # Reportes de ventas online
    path('servicio/<int:id>/solicitar/', views.formulario_servicios, name='formulario_servicios'),  # Ruta para ir al formulario de servicios
    path('transaccion_finalizada/', transaccion_finalizada, name='transaccion_finalizada'),  # Finalización de transacción de pago
    path('vaciar_carrito/', vaciar_carrito, name='vaciar_carrito'),  # Vaciar el carrito
    path('ver_detalles_producto/<int:producto_id>/', ver_detalles_producto, name='ver_detalles_producto'),  # Ver detalles del producto
    path('ver_detalles_servicio/<int:servicio_id>/', ver_detalles_servicio, name='ver_detalles_servicio'),  # Ver detalles del servicio
    path('ver_reportes', views.ver_reportes, name='ver_reportes'),  # Visualizar reportes
]
