from django.urls import path
from . import views

urlpatterns = [
    path('actualizar_datos_personales_cliente', views.actualizar_datos_personales_cliente, name='actualizar_datos_personales_cliente'),
    path('cambiar_contraseña_cliente', views.cambiar_contraseña_cliente, name='cambiar_contraseña_cliente'),
    path('gestionar_cuentas', views.gestionar_cuentas, name='gestionar_cuentas'),
    path('listar_clientes', views.listar_clientes, name="listar_clientes"),
    path('agregar_cliente', views.agregar_cliente, name="agregar_cliente"),
    path('editar_cliente/<int:cliente_id>', views.editar_cliente, name="editar_cliente"),
    path('borrar_cliente/<int:cliente_id>', views.borrar_cliente, name="borrar_cliente"),
    path('confirmar-borrar-cliente/<int:cliente_id>/', views.confirmar_borrar_cliente, name='confirmar_borrar_cliente'),
    path('listar_empleados', views.listar_empleados, name="listar_empleados"),
    path('agregar_empleado', views.agregar_empleado, name="agregar_empleado"),
    path('editar_empleado/<int:empleado_id>', views.editar_empleado, name="editar_empleado"),
    path('borrar_empleado/<int:empleado_id>', views.borrar_empleado, name="borrar_empleado"),
    path('confirmar-borrar-empleado/<int:empleado_id>/', views.confirmar_borrar_empleado, name='confirmar_borrar_empleado'),
]