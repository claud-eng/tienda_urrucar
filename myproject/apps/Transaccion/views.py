from .functions import es_administrador  # Importa la función 'es_administrador' para verificar si un usuario tiene rol de administrador.
from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

@user_passes_test(es_administrador, login_url='home')
def gestionar_inventario(request):
    """
    Permite al administrador gestionar el inventario de productos y servicios.
    """
    return render(request, 'Transaccion/gestionar_inventario.html')

@user_passes_test(es_administrador, login_url='home')
def gestionar_transacciones(request):
    """
    Vista para que los administradores gestionen todas las transacciones.
    """
    return render(request, 'Transaccion/gestionar_transacciones.html')

@user_passes_test(es_administrador, login_url='home')
def ver_reportes(request):
    """
    Vista para ver reportes de todas las transacciones.
    """
    return render(request, 'Transaccion/ver_reportes.html')

@user_passes_test(es_administrador, login_url='home')
def obtener_precio_producto(request):
    """
    Devuelve el precio del producto en formato JSON dado un ID de producto.
    """
    producto_id = request.GET.get('producto_id')

    try:
        producto = Producto.objects.get(id=producto_id)
        return JsonResponse({'precio': producto.precio})
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
