from django.urls import include, path  # Importa 'path' para definir rutas de URL y 'include' para incluir otras configuraciones de URL.
from . import views  # Importa las vistas definidas en el directorio actual.
from . import views_productos  # Importa el módulo que gestiona operaciones de productos.
from . import views_servicios  # Importa el módulo que gestiona operaciones de servicios.
from . import views_ventas  # Importa el módulo que maneja las ventas.
from .carrito import *  # Importa todas las funciones relacionadas con la gestión del carrito de compras.
from .functions import descargar_comprobante_pago  # Importa una función para descargar un comprobante de venta en formato PDF.
from .reports import * # Importa todas las funciones del archivo reports.
from .views import obtener_precio_producto # Importa una función para obtener el precio del producto.
from .webpay import iniciar_transaccion, transaccion_finalizada  # Importa funciones para iniciar y finalizar transacciones con Webpay.

urlpatterns = [
    path('agregar_al_carrito/producto/<int:id>/', agregar_al_carrito, {'tipo': 'producto'}, name='agregar_producto_al_carrito'),  # Agregar un producto al carrito
    path('agregar_al_carrito/servicio/<int:id>/', agregar_al_carrito, {'tipo': 'servicio'}, name='agregar_servicio_al_carrito'),  # Agregar un servicio al carrito
    path('agregar_producto', views_productos.agregar_producto, name="agregar_producto"),  # Ruta para agregar producto
    path('agregar_servicio', views_servicios.agregar_servicio, name="agregar_servicio"),  # Ruta para agregar servicio
    path('agregar_venta_manual_producto', views_ventas.agregar_venta_manual_producto, name='agregar_venta_manual_producto'),  # Ruta para agregar venta manual de un producto
    path('agregar_venta_manual_servicio', views_ventas.agregar_venta_manual_servicio, name='agregar_venta_manual_servicio'),  # Ruta para agregar venta manual de un servicio
    path('aumentar_cantidad/<int:item_id>/', aumentar_cantidad, name='aumentar_cantidad'),  # Aumentar cantidad de un ítem en el carrito
    path('borrar_producto/<int:producto_id>', views_productos.borrar_producto, name="borrar_producto"),  # Ruta para borrar producto
    path('borrar_servicio/<int:servicio_id>', views_servicios.borrar_servicio, name="borrar_servicio"),  # Ruta para borrar servicio
    path('carrito/', carrito, name='carrito'),  # Vista para ver el carrito
    path('catalogo_productos', views_productos.catalogo_productos, name='catalogo_productos'),  # Vista de catálogo de productos
    path('catalogo_servicios', views_servicios.catalogo_servicios, name='catalogo_servicios'),  # Vista de catálogo de servicios
    path('confirmar-borrar-producto/<int:producto_id>/', views_productos.confirmar_borrar_producto, name='confirmar_borrar_producto'),  # Confirmar borrado de producto
    path('confirmar-borrar-servicio/<int:servicio_id>/', views_servicios.confirmar_borrar_servicio, name='confirmar_borrar_servicio'),  # Confirmar borrado de servicio
    path('disminuir_cantidad/<int:item_id>/', disminuir_cantidad, name='disminuir_cantidad'),  # Disminuir cantidad de un ítem en el carrito
    path('editar_producto/<int:producto_id>', views_productos.editar_producto, name="editar_producto"),  # Editar un producto
    path('eliminar_imagen_adicional/<int:imagen_id>/', views_productos.eliminar_imagen_adicional, name='eliminar_imagen_adicional'),
    path('editar_servicio/<int:servicio_id>', views_servicios.editar_servicio, name="editar_servicio"),  # Editar un servicio
    path('editar_venta_manual_producto/<int:venta_id>/', views_ventas.editar_venta_manual_producto, name='editar_venta_manual_producto'), # Editar una venta manual de un producto
    path('editar_venta_manual_servicio/<int:venta_id>/', views_ventas.editar_venta_manual_servicio, name='editar_venta_manual_servicio'), # Editar una venta manual de un servicio
    path('editar-venta-online/<int:venta_id>/', views_ventas.editar_venta_online, name='editar_venta_online'), # Editar una venta online
    path('eliminar_del_carrito/<int:item_id>/', eliminar_del_carrito, name='eliminar_del_carrito'),  # Eliminar ítem del carrito
    path('generar_informe_inspeccion_pdf/', views.generar_informe_inspeccion_pdf, name='generar_informe_inspeccion_pdf'),  # Generar informe de inspección en formato PDF
    path('generar_presupuesto_pdf/', views.generar_presupuesto_pdf, name='generar_presupuesto_pdf'),  # Generar presupuesto en formato PDF
    path('gestionar_inventario', views.gestionar_inventario, name='gestionar_inventario'),  # Gestionar inventario (administrador)
    path('gestionar_transacciones', views.gestionar_transacciones, name='gestionar_transacciones'),  # Gestionar transacciones
    path('iniciar_transaccion/', iniciar_transaccion, name='iniciar_transaccion'),  # Iniciar transacción de pago
    path('listar_productos', views_productos.listar_productos, name="listar_productos"),  # Listar productos
    path('listar_servicios', views_servicios.listar_servicios, name="listar_servicios"),  # Listar servicios
    path('listar_ventas_manuales', views_ventas.listar_ventas_manuales, name='listar_ventas_manuales'),  # Listar ventas manuales
    path('listar_ventas_online', views_ventas.listar_ventas_online, name='listar_ventas_online'),  # Listar ventas online
    path('obtener-precio-producto/', obtener_precio_producto, name='obtener_precio_producto'),  # Obtener el precio de un producto en base a un ID
    path('producto/<int:producto_id>/galeria/<int:imagen_id>/', carrusel_completo, name='carrusel_completo'), # Carrusel de imágenes de productos
    path('realizar_compra/', realizar_compra, name='realizar_compra'),  # Realizar compra
    path('reporte_ventas_manuales', reporte_ventas_manuales, name='reporte_ventas_manuales'),  # Reportes de ventas manuales
    path('reporte_ventas_online', reporte_ventas_online, name='reporte_ventas_online'),  # Reportes de ventas online
    path('servicio/<int:id>/solicitar/', views_servicios.formulario_servicios, name='formulario_servicios'),  # Ruta para ir al formulario de servicios
    path('transaccion/descargar-comprobante/<str:tipo_venta>/<str:identificador>/', descargar_comprobante_pago, name='descargar_comprobante_pago'), # Descargar comprobante de pago en formato pdf
    path('transaccion_finalizada/', transaccion_finalizada, name='transaccion_finalizada'),  # Finalización de transacción de pago
    path('vaciar_carrito/', vaciar_carrito, name='vaciar_carrito'),  # Vaciar el carrito
    path('ver_detalles_producto/<int:producto_id>/', ver_detalles_producto, name='ver_detalles_producto'),  # Ver detalles del producto
    path('ver_detalles_servicio/<int:servicio_id>/', ver_detalles_servicio, name='ver_detalles_servicio'),  # Ver detalles del servicio
    path('ver_reportes', views.ver_reportes, name='ver_reportes'),  # Visualizar reportes
]
