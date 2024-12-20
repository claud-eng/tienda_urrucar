from django.contrib import messages  # Importa la funcionalidad para mostrar mensajes al usuario.
from django.contrib.auth.decorators import login_required  # Importa el decorador para requerir inicio de sesión en vistas.
from django.contrib.contenttypes.models import ContentType  # Importa ContentType para trabajar con tipos de contenido genéricos.
from django.db import transaction  # Importa transaction para manejar transacciones atómicas en la base de datos.
from django.http import Http404, HttpResponseRedirect  # Importa Http404 para manejar errores de "No encontrado" y HttpResponseRedirect para redireccionar respuestas HTTP.
from django.shortcuts import get_object_or_404, render, redirect  # Importa funciones auxiliares para manejo de vistas y redirecciones.
from .models import Carrito, Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, Producto, Servicio  # Importa modelos específicos usados en la aplicación.
from .forms import ClienteAnonimoForm # Importa formulario para gestionar a los clientes anónimos.
from .views import formato_precio  # Importa la función de formato de precio desde views.

def obtener_session_key(request, reset=False):
    """
    Obtiene o genera un identificador único para la sesión del navegador.
    Si reset=True, fuerza la creación de un nuevo session_key.
    """
    if reset:
        request.session.flush()  # Limpia la sesión actual
        request.session.create()  # Crea una nueva sesión con un nuevo session_key
    elif not request.session.session_key:
        request.session.create()

    return request.session.session_key

def ver_detalles_producto(request, producto_id):
    """
    Muestra los detalles de un producto y permite agregarlo al carrito.
    Si se realiza una solicitud POST, se agrega al carrito con lógica especial
    para productos de categoría 'Vehículo'.
    """
    producto = get_object_or_404(Producto, id=producto_id)
    producto.precio_formateado = formato_precio(producto.precio)
    if producto.precio_reserva:
        producto.precio_reserva_formateado = formato_precio(producto.precio_reserva)
    else:
        producto.precio_reserva_formateado = None

    # Recuperar imágenes adicionales relacionadas
    imagenes_adicionales = producto.imagenes.all()

    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))

        # Validar cantidad para productos que no son vehículos
        if producto.categoria == "Vehículo":
            cantidad = 1  # Cantidad fija para vehículos
        elif cantidad <= 0 or cantidad > producto.cantidad_stock:
            return render(request, 'Transaccion/ver_detalles_producto.html', {
                'producto': producto,
                'imagenes_adicionales': imagenes_adicionales,
                'error_message': 'Cantidad no válida',
            })

        # Obtiene la instancia del cliente
        cliente = Cliente.objects.get(user=request.user)

        # Verifica si el producto ya está en el carrito
        carrito_item = Carrito.objects.filter(
            cliente=cliente,
            content_type=ContentType.objects.get_for_model(Producto),
            object_id=producto.id,
            carrito=1
        ).first()

        if carrito_item:
            if producto.categoria == "Vehículo":
                # No permitir modificar la cantidad de vehículos
                messages.warning(request, 'El vehículo ya está en el carrito y no se puede modificar la cantidad.')
            else:
                # Si no es vehículo, actualizar cantidad
                carrito_item.cantidad += cantidad
                carrito_item.save()
        else:
            # Crear un nuevo ítem en el carrito
            carrito_item = Carrito(
                cliente=cliente,
                content_type=ContentType.objects.get_for_model(Producto),
                object_id=producto.id,
                cantidad=cantidad,
                carrito=1
            )
            carrito_item.save()

        return redirect('carrito')

    return render(request, 'Transaccion/ver_detalles_producto.html', {
        'producto': producto,
        'imagenes_adicionales': imagenes_adicionales
    })

def ver_detalles_servicio(request, servicio_id):
    """
    Muestra los detalles de un servicio y permite agregarlo al carrito.
    Si se realiza una solicitud POST, se agrega al carrito con la cantidad indicada.
    """
    servicio = get_object_or_404(Servicio, id=servicio_id)
    servicio.precio_formateado = formato_precio(servicio.precio)

    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))

        # Validar cantidad
        if cantidad <= 0:
            return render(request, 'Transaccion/ver_detalles_servicio.html', {
                'servicio': servicio,
                'error_message': 'Cantidad no válida',
            })

        # Obtener la instancia del cliente
        cliente = Cliente.objects.get(user=request.user)

        # Verifica si el servicio ya está en el carrito
        carrito_item = Carrito.objects.filter(
            cliente=cliente,
            content_type=ContentType.objects.get_for_model(Servicio),
            object_id=servicio.id,
            carrito=1
        ).first()

        if carrito_item:
            # Incrementar la cantidad del servicio
            carrito_item.cantidad += cantidad
            carrito_item.save()
        else:
            # Crear un nuevo ítem en el carrito
            carrito_item = Carrito(
                cliente=cliente,
                content_type=ContentType.objects.get_for_model(Servicio),
                object_id=servicio.id,
                cantidad=cantidad,
                carrito=1
            )
            carrito_item.save()

        return redirect('carrito')

    return render(request, 'Transaccion/ver_detalles_servicio.html', {
        'servicio': servicio,
    })

def agregar_al_carrito(request, id, tipo):
    """
    Agrega un producto o servicio al carrito. Si el producto pertenece a la categoría
    'Vehículo', utiliza el precio de reserva y establece la cantidad en 1.
    """
    cantidad = int(request.POST.get('cantidad', 1))
    cliente = None
    cliente_anonimo = None

    if request.user.is_authenticated:
        # Si el usuario está autenticado, obtener su cliente asociado
        try:
            cliente = Cliente.objects.get(user=request.user)
        except Cliente.DoesNotExist:
            messages.error(request, "Tu cuenta no está asociada a un cliente.")
            return redirect('carrito')
    else:
        # Si el usuario no está autenticado, obtener o crear un cliente anónimo
        session_key = obtener_session_key(request)
        cliente_anonimo = ClienteAnonimo.objects.filter(session_key=session_key).first()

        if not cliente_anonimo:
            # Crear un nuevo cliente anónimo si no existe
            cliente_anonimo = ClienteAnonimo.objects.create(
                nombre="Anónimo",
                apellido="",
                email=f"anonimo_{session_key}@example.com",
                numero_telefono="",
                session_key=session_key,
            )
            request.session['cliente_anonimo_id'] = cliente_anonimo.id

    # Verificar el tipo de ítem (producto o servicio)
    if tipo == 'producto':
        item = get_object_or_404(Producto, id=id)
        content_type = ContentType.objects.get_for_model(Producto)
        if item.categoria == "Vehículo":
            cantidad = 1
    elif tipo == 'servicio':
        item = get_object_or_404(Servicio, id=id)
        content_type = ContentType.objects.get_for_model(Servicio)
    else:
        raise Http404("Tipo no válido")

    # Buscar el ítem en el carrito
    carrito_item = Carrito.objects.filter(
        cliente=cliente,
        cliente_anonimo=cliente_anonimo,
        session_key=request.session.session_key,
        content_type=content_type,
        object_id=id,
        carrito=1,
    ).first()

    if carrito_item:
        if tipo == 'producto' and item.categoria == "Vehículo":
            messages.warning(request, 'El vehículo ya está en el carrito y no se puede modificar la cantidad.')
        else:
            carrito_item.cantidad += cantidad
            carrito_item.save()
    else:
        Carrito.objects.create(
            cliente=cliente,
            cliente_anonimo=cliente_anonimo,
            session_key=request.session.session_key,
            content_type=content_type,
            object_id=id,
            cantidad=cantidad,
            carrito=1,
        )

    return redirect('carrito')

# Ajustar la vista del carrito
def carrito(request):
    """
    Muestra el contenido actual del carrito y gestiona la información de los clientes no registrados.
    """
    cliente = None
    cliente_form = None
    carrito_items = None
    session_key = request.session.session_key

    # Asegurar que la sesión exista
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    if request.user.is_authenticated:
        # Cliente autenticado
        cliente = Cliente.objects.get(user=request.user)
        carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
    else:
        # Cliente anónimo
        cliente_anonimo_id = request.session.get('cliente_anonimo_id')
        if cliente_anonimo_id:
            cliente_anonimo = ClienteAnonimo.objects.filter(id=cliente_anonimo_id).first()
        else:
            cliente_anonimo = ClienteAnonimo.objects.filter(session_key=session_key).first()

        # Si no existe un cliente anónimo, crearlo
        if not cliente_anonimo:
            cliente_anonimo = ClienteAnonimo.objects.create(
                nombre="Anónimo",
                apellido="",
                email=f"anonimo_{session_key}@example.com",
                session_key=session_key
            )
            request.session['cliente_anonimo_id'] = cliente_anonimo.id

        # Obtener los ítems del carrito para el cliente anónimo
        carrito_items = Carrito.objects.filter(cliente_anonimo=cliente_anonimo, carrito=1)

        # Crear una instancia del formulario para usuarios no registrados
        cliente_form = ClienteAnonimoForm()

    # Calcula y formatea el precio total del carrito
    total = sum(item.obtener_precio_total() for item in carrito_items)
    total_formateado = formato_precio(total)

    # Agrega información adicional y formatea precios para cada elemento en el carrito
    for item in carrito_items:
        item.precio_formateado = formato_precio(item.item.precio)
        item.precio_total_formateado = formato_precio(item.obtener_precio_total())
        item.es_servicio = isinstance(item.item, Servicio)
        
        # Formatear el precio de reserva si aplica
        if isinstance(item.item, Producto) and item.item.precio_reserva:
            item.item.precio_reserva_formateado = formato_precio(item.item.precio_reserva)
        else:
            item.item.precio_reserva_formateado = None

    # Procesa el formulario para clientes anónimos
    if request.method == 'POST' and not request.user.is_authenticated:
        cliente_form = ClienteAnonimoForm(request.POST)
        if cliente_form.is_valid():
            cliente_anonimo = cliente_form.save()  # Guarda la información del cliente anónimo
            request.session['cliente_anonimo_id'] = cliente_anonimo.id  # Guarda el ID del cliente en la sesión
            return redirect('realizar_compra')

    return render(request, 'Transaccion/carrito.html', {
        'carrito_items': carrito_items,
        'total': total_formateado,
        'cliente_form': cliente_form
    })

def realizar_compra(request):
    """
    Procesa la compra de los productos/servicios en el carrito y gestiona tanto clientes registrados como anónimos.
    """
    cliente = None
    cliente_anonimo = None

    if request.user.is_authenticated:
        # Cliente autenticado
        cliente = Cliente.objects.get(user=request.user)
        carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
    else:
        # Cliente anónimo
        session_key = request.session.session_key
        if not session_key:
            messages.error(request, "No se ha encontrado información de la sesión.")
            return redirect('carrito')

        cliente_anonimo = ClienteAnonimo.objects.filter(session_key=session_key).first()
        if not cliente_anonimo:
            messages.error(request, "Tu información no está registrada. Completa los datos primero.")
            return redirect('carrito')

        carrito_items = Carrito.objects.filter(session_key=session_key, carrito=1)

    # Verifica si el carrito está vacío
    if not carrito_items.exists():
        messages.error(request, "Tu carrito está vacío.")
        return redirect('carrito')

    # Calcula el total del carrito
    total = sum(item.obtener_precio_total() for item in carrito_items)

    # Crear la orden de compra
    orden = VentaOnline.objects.create(
        cliente=cliente,
        cliente_anonimo=cliente_anonimo,
        total=total
    )

    # Crear los detalles de la orden
    for item in carrito_items:
        if isinstance(item.item, Producto):
            DetalleVentaOnline.objects.create(
                orden_compra=orden,
                producto=item.item,
                precio=item.item.precio,
                cantidad=item.cantidad
            )
        elif isinstance(item.item, Servicio):
            DetalleVentaOnline.objects.create(
                orden_compra=orden,
                servicio=item.item,
                precio=item.item.precio,
                cantidad=item.cantidad
            )

    # Limpiar el carrito
    carrito_items.delete()

    messages.success(request, "Compra realizada con éxito.")
    return render(request, 'Transaccion/compra_exitosa.html', {'orden': orden})

def eliminar_del_carrito(request, item_id):
    """
    Elimina un elemento específico del carrito del cliente autenticado o anónimo.
    """
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    carrito_item = None

    if request.user.is_authenticated:
        cliente = Cliente.objects.get(user=request.user)
        carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()
    else:
        carrito_item = Carrito.objects.filter(id=item_id, session_key=session_key, carrito=1).first()

    if carrito_item:
        carrito_item.delete()
        messages.success(request, 'El ítem fue eliminado del carrito.')
    else:
        messages.error(request, 'El ítem no existe o no pertenece a tu carrito.')

    return redirect('carrito')

def vaciar_carrito(request):
    """
    Vacía completamente el carrito de compras del cliente autenticado o anónimo.
    """
    cliente = None
    cliente_anonimo = None
    carrito_items = None

    # Si el usuario está autenticado
    if request.user.is_authenticated:
        try:
            cliente = Cliente.objects.get(user=request.user)
            carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
        except Cliente.DoesNotExist:
            messages.error(request, "Tu cuenta no está asociada a un cliente.")
            return redirect('carrito')
    else:
        # Si el usuario no está autenticado, manejar cliente anónimo
        session_key = request.session.session_key
        if not session_key:
            messages.info(request, "No hay un carrito para eliminar.")
            return redirect('carrito')

        cliente_anonimo = ClienteAnonimo.objects.filter(session_key=session_key).first()
        if cliente_anonimo:
            carrito_items = Carrito.objects.filter(cliente_anonimo=cliente_anonimo, carrito=1)
        else:
            messages.info(request, "El carrito ya está vacío.")
            return redirect('carrito')

    # Eliminar los elementos del carrito si existen
    if carrito_items.exists():
        carrito_items.delete()
        messages.success(request, 'Se vació el carrito correctamente.')
    else:
        messages.info(request, 'El carrito ya estaba vacío.')

    return redirect('carrito')

def aumentar_cantidad(request, item_id):
    """
    Aumenta la cantidad de un elemento en el carrito, excepto si el producto pertenece
    a la categoría 'Vehículo'.
    """
    cliente = None
    cliente_anonimo = None
    carrito_item = None

    if request.user.is_authenticated:
        # Cliente autenticado
        cliente = Cliente.objects.get(user=request.user)
        carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()
    else:
        # Cliente anónimo
        session_key = request.session.session_key
        if not session_key:
            messages.error(request, "No se ha encontrado una sesión válida.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        carrito_item = Carrito.objects.filter(id=item_id, session_key=session_key, carrito=1).first()

    # Verificar el ítem y aplicar lógica
    if carrito_item:
        if isinstance(carrito_item.item, Producto) and carrito_item.item.categoria == "Vehículo":
            messages.warning(request, 'No se puede aumentar la cantidad de un vehículo en el carrito.')
        else:
            carrito_item.cantidad += 1
            carrito_item.save()
            messages.success(request, 'Se incrementó la cantidad del ítem.')
    else:
        messages.error(request, 'El ítem no existe en tu carrito.')

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def disminuir_cantidad(request, item_id):
    """
    Disminuye la cantidad de un elemento en el carrito, excepto si el producto pertenece
    a la categoría 'Vehículo'.
    """
    cliente = None
    cliente_anonimo = None
    carrito_item = None

    if request.user.is_authenticated:
        # Cliente autenticado
        cliente = Cliente.objects.get(user=request.user)
        carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()
    else:
        # Cliente anónimo
        session_key = request.session.session_key
        if not session_key:
            messages.error(request, "No se ha encontrado una sesión válida.")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

        carrito_item = Carrito.objects.filter(id=item_id, session_key=session_key, carrito=1).first()

    # Verificar el ítem y aplicar lógica
    if carrito_item:
        if isinstance(carrito_item.item, Producto) and carrito_item.item.categoria == "Vehículo":
            messages.warning(request, 'No se puede disminuir la cantidad de un vehículo en el carrito.')
        elif carrito_item.cantidad > 1:
            carrito_item.cantidad -= 1
            carrito_item.save()
            messages.success(request, 'Se redujo la cantidad del ítem.')
        else:
            messages.info(request, 'La cantidad mínima es 1. El ítem no puede ser reducido más.')
    else:
        messages.error(request, 'El ítem no existe en tu carrito.')

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
