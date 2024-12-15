from django.contrib.contenttypes.models import ContentType  # Importa ContentType para trabajar con relaciones de contenido genéricas en Django.
from .models import *  # Importa todos los modelos definidos en el módulo models de la aplicación actual.
from collections import Counter
from django.db.models import Count
from collections import OrderedDict

# Devuelve el conteo de elementos en el carrito del cliente autenticado.
def carrito_count(request):
    if request.user.is_authenticated:
        cliente = Cliente.objects.filter(user=request.user).first()
        if cliente:
            count = Carrito.objects.filter(cliente=cliente, carrito=1).count()
            return {'carrito_count': count}
    return {'carrito_count': 0}

# Formatea el número utilizando comas como separadores de miles y luego reemplaza por puntos
def formato_precio(precio):
    try:
        precio = int(precio)
        return f"{precio:,}".replace(",", ".")
    except (ValueError, TypeError):
        return precio

# Agrega la función de formato de precio al contexto global.
def agregar_formato_precio(request):
    return {'formato_precio': formato_precio}

# Agrega la función de poder filtrar por marca en el catálogo de productos
def agregar_filtros_catalogo(request):
    """
    Prepara los datos para la relación dinámica entre marcas y sus conteos.
    """
    # Obtener marcas y sus conteos directamente de la base de datos
    marcas = Producto.objects.values('marca').annotate(total=Count('marca')).order_by('marca')

    # Crear una estructura para enviar al template
    marca_count = {marca['marca']: marca['total'] for marca in marcas}

    return {
        'marca_count': marca_count,
    }