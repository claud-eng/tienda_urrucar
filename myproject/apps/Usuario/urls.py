from django.conf.urls.static import static  # Importa la función 'static' para manejar archivos estáticos en la configuración de URL.
from django.urls import path  # Importa la función 'path' para definir rutas URL en Django.
from . import views  # Importa el módulo 'views' desde el directorio actual para usar las vistas definidas en la aplicación.

urlpatterns = [
    path('actualizar_datos_personales_cliente', views.actualizar_datos_personales_cliente, name='actualizar_datos_personales_cliente'),  # Actualizar datos personales del cliente
    path('agregar_cliente', views.agregar_cliente, name="agregar_cliente"),  # Agregar un cliente
    path('agregar_empleado', views.agregar_empleado, name="agregar_empleado"),  # Agregar un empleado
    path('borrar_cliente/<int:cliente_id>', views.borrar_cliente, name="borrar_cliente"),  # Borrar un cliente
    path('borrar_empleado/<int:empleado_id>', views.borrar_empleado, name="borrar_empleado"),  # Borrar un empleado
    path('cambiar_contraseña_cliente', views.cambiar_contraseña_cliente, name='cambiar_contraseña_cliente'),  # Cambiar la contraseña del cliente
    path('confirmar-borrar-cliente/<int:cliente_id>/', views.confirmar_borrar_cliente, name='confirmar_borrar_cliente'),  # Confirmar borrado del cliente
    path('confirmar-borrar-empleado/<int:empleado_id>/', views.confirmar_borrar_empleado, name='confirmar_borrar_empleado'),  # Confirmar borrado del empleado
    path('editar_cliente/<int:cliente_id>', views.editar_cliente, name="editar_cliente"),  # Editar un cliente
    path('editar_empleado/<int:empleado_id>', views.editar_empleado, name="editar_empleado"),  # Editar un empleado
    path('gestionar_cuentas', views.gestionar_cuentas, name='gestionar_cuentas'),  # Gestionar cuentas
    path('listar_clientes', views.listar_clientes, name="listar_clientes"),  # Listar clientes
    path('listar_empleados', views.listar_empleados, name="listar_empleados"),  # Listar empleados
]

