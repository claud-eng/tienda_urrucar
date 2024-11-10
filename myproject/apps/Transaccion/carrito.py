from django.contrib import messages  # Importa la funcionalidad para mostrar mensajes al usuario.
from django.contrib.auth.decorators import login_required  # Importa el decorador para requerir inicio de sesión en vistas.
from django.contrib.contenttypes.models import ContentType  # Importa ContentType para trabajar con tipos de contenido genéricos.
from django.db import transaction  # Importa transaction para manejar transacciones atómicas en la base de datos.
from django.http import Http404, HttpResponseRedirect  # Importa Http404 para manejar errores de "No encontrado" y HttpResponseRedirect para redireccionar respuestas HTTP.
from django.shortcuts import get_object_or_404, render, redirect  # Importa funciones auxiliares para manejo de vistas y redirecciones.
from .models import Carrito, Cliente, DetalleVentaOnline, VentaOnline, Producto, Servicio  # Importa modelos específicos usados en la aplicación.
from .views import formato_precio  # Importa la función de formato de precio desde views.

def ver_detalles_producto(request, producto_id):
    """
    Muestra los detalles de un producto y permite agregarlo al carrito.
    Si se realiza una solicitud POST, se agrega la cantidad especificada al carrito,
    validando que no exceda el stock disponible.
    """
    producto = get_object_or_404(Producto, id=producto_id)
    producto.precio_formateado = formato_precio(producto.precio)

    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))

        if cantidad <= 0 or cantidad > producto.cantidad_stock:
            return render(request, 'Transaccion/ver_detalles_producto.html', {
                'producto': producto,
                'error_message': 'Cantidad no válida',
            })

        # Obtiene la instancia del cliente
        cliente = Cliente.objects.get(user=request.user)

        carrito_item = Carrito.objects.filter(cliente=cliente, content_type=ContentType.objects.get_for_model(Producto), object_id=producto.id, carrito=1).first()

        if carrito_item:
            # Si el producto ya está en el carrito, se actualiza la cantidad
            carrito_item.cantidad += cantidad
            carrito_item.save()
        else:
            # Si no está en el carrito, crea un nuevo registro
            carrito_item = Carrito(
                cliente=cliente,
                content_type=ContentType.objects.get_for_model(Producto),
                object_id=producto.id,
                cantidad=cantidad,
                carrito=1
            )
            carrito_item.save()
        
        return redirect('carrito')

    return render(request, 'Transaccion/ver_detalles_producto.html', {'producto': producto})

def agregar_al_carrito(request, id, tipo):
    """
    Agrega un producto o servicio al carrito, dependiendo del tipo especificado.
    Si el producto ya está en el carrito, se incrementa su cantidad; si es un servicio,
    se muestra un mensaje de error.
    """
    cantidad = int(request.POST.get('cantidad', 1))
    cliente = Cliente.objects.get(user=request.user)

    if tipo == 'producto':
        item = get_object_or_404(Producto, id=id)
        content_type = ContentType.objects.get_for_model(Producto)
    elif tipo == 'servicio':
        item = get_object_or_404(Servicio, id=id)
        content_type = ContentType.objects.get_for_model(Servicio)
    else:
        # Manejar error o redirigir a una página de error
        pass

    carrito_item = Carrito.objects.filter(cliente=cliente, content_type=content_type, object_id=id, carrito=1).first()

    if carrito_item:
        if tipo == 'servicio':
            # Si es un servicio y ya está en el carrito, muestra un mensaje de error
            messages.error(request, 'El servicio ya se encuentra en el carrito.')
        else:
            # Si es un producto, actualiza la cantidad
            carrito_item.cantidad += cantidad
            carrito_item.save()
    else:
        # Si no está en el carrito, crea un nuevo registro
        carrito_item = Carrito(
            cliente=cliente,
            content_type=content_type,
            object_id=id,
            cantidad=cantidad,
            carrito=1
        )
        carrito_item.save()

    return redirect('carrito')

def carrito(request):
    """
    Muestra el contenido actual del carrito para el cliente autenticado,
    calculando y formateando el precio total de los elementos.
    """
    cliente = Cliente.objects.get(user=request.user)
    carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)

    # Calcula y formatea el precio total del carrito
    total = sum(item.obtener_precio_total() for item in carrito_items)
    total_formateado = formato_precio(total)

    # Agrega información adicional y formatea precios para cada elemento en el carrito
    for item in carrito_items:
        item.precio_formateado = formato_precio(item.item.precio)
        item.precio_total_formateado = formato_precio(item.obtener_precio_total())
        item.es_servicio = isinstance(item.item, Servicio)

    return render(request, 'Transaccion/carrito.html', {
        'carrito_items': carrito_items,
        'total': total_formateado
    })

def realizar_compra(request):
    """
    Renderiza la página para proceder con la compra de los productos y servicios
    en el carrito.
    """
    return render(request, 'Transaccion/realizar_compra.html')

def eliminar_del_carrito(request, item_id):
    """
    Elimina un elemento específico del carrito del cliente.
    Si el elemento no existe o no pertenece al cliente, devuelve un error 404.
    """
    cliente = Cliente.objects.get(user=request.user)
    carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()

    if carrito_item is not None:
        carrito_item.delete()
    else:
        raise Http404("El elemento que intentas eliminar no existe o no te pertenece")

    return redirect('carrito')

def vaciar_carrito(request):
    """
    Vacía completamente el carrito de compras del cliente autenticado.
    """
    cliente = Cliente.objects.get(user=request.user)
    carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
    carrito_items.delete()

    return redirect('carrito')

def aumentar_cantidad(request, item_id):
    """
    Aumenta la cantidad de un elemento en el carrito en uno, según el `item_id`.
    """
    cliente = Cliente.objects.get(user=request.user)
    carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()

    if carrito_item:
        carrito_item.cantidad += 1
        carrito_item.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def disminuir_cantidad(request, item_id):
    """
    Disminuye la cantidad de un elemento en el carrito en uno, solo si la cantidad
    actual es mayor a uno, para evitar cantidades negativas.
    """
    cliente = Cliente.objects.get(user=request.user)
    carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()

    if carrito_item and carrito_item.cantidad > 1:
        carrito_item.cantidad -= 1
        carrito_item.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@transaction.atomic
def crear_orden_de_compra(usuario, carrito_items, total):
    """
    Crea una orden de compra en la base de datos y asocia los elementos del
    carrito a dicha orden. Luego marca los elementos del carrito como comprados.

    :param usuario: El usuario que está realizando la compra
    :param carrito_items: Los ítems en el carrito de compras
    :param total: El monto total de la orden
    :return: La instancia de la orden de compra creada
    """
    cliente = Cliente.objects.get(user=usuario)
    # Crear la orden de compra
    orden = VentaOnline.objects.create(cliente=cliente, total=total)
    
    # Asocia los elementos del carrito a la orden de compra
    for item in carrito_items:
        detalle_orden_kwargs = {
            'orden_compra': orden,
            'precio': item.item.precio,
            'cantidad': item.cantidad
        }
        if isinstance(item.item, Producto):
            detalle_orden_kwargs['producto'] = item.item
        else:
            detalle_orden_kwargs['servicio'] = item.item
        
        DetalleVentaOnline.objects.create(**detalle_orden_kwargs)
    
    # Marca los elementos del carrito como comprados
    carrito_items.update(carrito=0)  # `carrito=0` indica que los ítems fueron comprados

    return orden
