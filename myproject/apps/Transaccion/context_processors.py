from collections import Counter  # Importa Counter para contar elementos de forma eficiente en estructuras iterables.
from collections import OrderedDict  # Importa OrderedDict para crear diccionarios que mantienen el orden de inserción.
from django.contrib.contenttypes.models import ContentType  # Importa ContentType para trabajar con relaciones de contenido genéricas en Django.
from django.db.models import Count  # Importa Count para realizar conteos agregados en consultas de modelos.
from .models import *  # Importa todos los modelos definidos en el módulo models de la aplicación actual.

# Devuelve el conteo de elementos en el carrito del cliente autenticado.
def carrito_count(request):
    """
    Devuelve el conteo de elementos en el carrito del cliente autenticado o anónimo.
    """
    count = 0

    if request.user.is_authenticated:
        # Cliente autenticado
        cliente = Cliente.objects.filter(user=request.user).first()
        if cliente:
            count = Carrito.objects.filter(cliente=cliente, carrito=1).count()
    else:
        # Cliente anónimo
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        count = Carrito.objects.filter(session_key=session_key, carrito=1).count()

    return {'carrito_count': count}

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