from django.contrib.auth.signals import user_logged_out  # Señal para detectar cierre de sesión.
from django.contrib.sessions.models import Session  # Modelo para manejar sesiones.
from django.dispatch import receiver  # Decorador para conectar señales.
from .models import Carrito, Cliente  # Modelos personalizados.

@receiver(user_logged_out)
def limpiar_carrito_al_deslogearse(sender, request, user, **kwargs):
    """
    Limpia el carrito cuando un usuario autenticado desloguea.
    """
    if user.is_authenticated:
        try:
            # Obtener el cliente asociado al usuario
            cliente = Cliente.objects.get(user=user)
            # Limpiar los ítems del carrito del cliente
            Carrito.objects.filter(cliente=cliente, carrito=1).delete()
            print(f"Carrito limpiado para el usuario {user.username}")
        except Cliente.DoesNotExist:
            print(f"No se encontró un cliente asociado para el usuario {user.username}")
