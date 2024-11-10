from django.contrib.contenttypes.models import ContentType  # Importa ContentType para trabajar con relaciones de contenido genéricas en Django.
from .models import *  # Importa todos los modelos definidos en el módulo models de la aplicación actual.

def carrito_count(request):
    if request.user.is_authenticated:
        cliente = Cliente.objects.filter(user=request.user).first()
        if cliente:
            count = Carrito.objects.filter(cliente=cliente, carrito=1).count()
            return {'carrito_count': count}
    return {'carrito_count': 0}

def formato_precio(precio):
    try:
        # Formatea el número utilizando comas como separadores de miles y luego reemplaza por puntos
        precio = int(precio)
        return f"{precio:,}".replace(",", ".")
    except (ValueError, TypeError):
        return precio

def agregar_formato_precio(request):
    return {'formato_precio': formato_precio}