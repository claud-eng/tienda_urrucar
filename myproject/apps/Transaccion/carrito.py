from django.contrib import messages  # Importa la funcionalidad para mostrar mensajes al usuario.
from django.contrib.auth.decorators import login_required  # Importa el decorador para requerir inicio de sesión en vistas.
from django.contrib.contenttypes.models import ContentType  # Importa ContentType para trabajar con tipos de contenido genéricos.
from django.db import transaction  # Importa transaction para manejar transacciones atómicas en la base de datos.
from django.http import Http404, HttpResponseRedirect  # Importa Http404 para manejar errores de "No encontrado" y HttpResponseRedirect para redireccionar respuestas HTTP.
from django.shortcuts import get_object_or_404, render, redirect  # Importa funciones auxiliares para manejo de vistas y redirecciones.
from django.utils.crypto import get_random_string  # Importa función para generar cadenas aleatorias seguras.
from .forms import ClienteAnonimoForm  # Importa formulario para gestionar a los clientes anónimos.
from .models import Carrito, Cliente, ClienteAnonimo, DetalleVentaOnline, Producto, Servicio, VentaOnline  # Importa modelos específicos usados en la aplicación.
from .views import formato_precio  # Importa la función de formato de precio desde views.

def obtener_session_key(request, reset=False, forzar_anonimo=False):
    """
    Obtiene o genera un identificador único para la sesión del navegador.
    Si reset=True, fuerza la creación de un nuevo session_key.
    Si forzar_anonimo=True, genera un nuevo session_key anónimo sin usar la sesión del request.
    """
    if forzar_anonimo:
        # Genera un session_key único para clientes anónimos
        while True:
            session_key = 'anonimo_' + get_random_string(20)
            if not ClienteAnonimo.objects.filter(session_key=session_key).exists():
                return session_key
    else:
        if reset:
            request.session.flush()
            request.session.create()
        elif not request.session.session_key:
            request.session.create()

        return request.session.session_key

def ver_detalles_producto(request, producto_id):
    """
    Muestra los detalles de un producto y permite agregarlo al carrito.
    Si se realiza una solicitud POST, se agrega al carrito con lógica especial
    para productos de categoría 'Vehículo'.
    También establece la imagen activa en el carrusel basada en la última imagen vista.
    """
    producto = get_object_or_404(Producto, id=producto_id)
    producto.precio_formateado = formato_precio(producto.precio)

    if producto.precio_reserva:
        producto.precio_reserva_formateado = formato_precio(producto.precio_reserva)
    else:
        producto.precio_reserva_formateado = None

    # Recuperar imágenes adicionales relacionadas
    imagenes_adicionales = list(producto.imagenes.all())

    # Manejar la imagen activa desde la URL
    imagen_id = request.GET.get("imagen_id", None)
    imagen_index = 0  # Por defecto, la imagen principal

    if imagen_id:
        try:
            imagen_id = int(imagen_id)  # Convertir a entero
            for index, imagen in enumerate(imagenes_adicionales):
                if imagen.id == imagen_id:
                    imagen_index = index + 1  # +1 porque la imagen principal está en la posición 0
                    break
        except ValueError:
            imagen_index = 0  # Si hay un error, usar la imagen principal

    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))

        # Validar cantidad para productos que no son vehículos
        if producto.categoria == "Vehículo":
            cantidad = 1  # Cantidad fija para vehículos
        elif cantidad <= 0 or cantidad > producto.cantidad_stock:
            return render(request, 'Transaccion/ver_detalles_producto.html', {
                'producto': producto,
                'imagenes_adicionales': imagenes_adicionales,
                'imagen_index': imagen_index,
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
        'imagenes_adicionales': imagenes_adicionales,
        'imagen_index': imagen_index,  # Pasamos el índice de la imagen activa
    })

def carrusel_completo(request, producto_id, imagen_id=None):
    producto = get_object_or_404(Producto, id=producto_id)
    
    # Obtener todas las imágenes adicionales del producto
    imagenes = list(producto.imagenes.all())  # Lista de imágenes adicionales
    
    # Agregar la imagen principal al inicio con un identificador especial
    if producto.imagen:
        imagen_principal = {
            'url': producto.imagen.url,
            'is_main': True,  # Marcar como imagen principal
        }
        imagenes.insert(0, imagen_principal)  # Agregar la imagen principal primero

    # Determinar la imagen inicial en el carrusel
    imagen_index = 0
    if imagen_id and imagen_id != 0:
        for index, img in enumerate(imagenes):
            if isinstance(img, dict):  # La imagen principal no tiene ID
                continue
            if str(img.id) == str(imagen_id):  # Comparar ID de imágenes adicionales
                imagen_index = index
                break

    return render(request, 'Transaccion/carrusel_completo.html', {
        'producto': producto,
        'imagenes': imagenes,
        'imagen_index': imagen_index
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
    Agrega un producto o servicio al carrito. 
    - Si el producto pertenece a la categoría 'Vehículo', usa el precio de reserva y cantidad 1.
    - Solo se permite un producto de categoría 'Vehículo' en el carrito.
    - Solo se permite un producto o un servicio en el carrito a la vez.
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
            cliente_anonimo = ClienteAnonimo.objects.create(
                nombre="Anónimo",
                apellido="",
                email=f"anonimo_{session_key}@example.com",
                numero_telefono="",
                session_key=session_key,
            )
            request.session['cliente_anonimo_id'] = cliente_anonimo.id

    # Obtener todos los elementos en el carrito del usuario
    items_en_carrito = Carrito.objects.filter(
        cliente=cliente,
        cliente_anonimo=cliente_anonimo,
        session_key=request.session.session_key,
        carrito=1,
    )

    # Validación para permitir solo un producto o un servicio en el carrito
    if items_en_carrito.exists():
        primer_item = items_en_carrito.first()
        primer_item_tipo = primer_item.content_type.model  # 'producto' o 'servicio'

        if (tipo == 'producto' and primer_item_tipo == 'servicio') or (tipo == 'servicio' and primer_item_tipo == 'producto'):
            messages.error(request, "No puedes agregar un producto si ya tienes un servicio en el carrito, y viceversa.")
            return redirect('carrito')

    # Lógica para productos
    if tipo == 'producto':
        item = get_object_or_404(Producto, id=id)

        # Si el producto es de categoría 'Vehículo', solo se permite 1 en el carrito
        if item.categoria == "Vehículo":
            cantidad = 1  # Asegurar que la cantidad sea 1 para vehículos

            # Obtener productos en el carrito
            productos_en_carrito = Carrito.objects.filter(
                cliente=cliente,
                cliente_anonimo=cliente_anonimo,
                session_key=request.session.session_key,
                content_type=ContentType.objects.get_for_model(Producto),
                carrito=1,
            )

            # Verificar si ya hay un vehículo en el carrito
            for carrito_item in productos_en_carrito:
                producto = Producto.objects.get(id=carrito_item.object_id)
                if producto.categoria == "Vehículo":
                    messages.error(request, 'Solo puedes tener un producto de categoría "Vehículo" en el carrito.')
                    return redirect('carrito')

        content_type = ContentType.objects.get_for_model(Producto)

    # Lógica para servicios
    elif tipo == 'servicio':
        item = get_object_or_404(Servicio, id=id)

        # No permitir agregar servicios con precio 0
        if item.precio <= 0:
            messages.error(request, 'No se pueden agregar servicios con precio 0 al carrito.')
            return redirect('carrito')

        # Validar que no haya más de un servicio en el carrito
        servicios_en_carrito = Carrito.objects.filter(
            cliente=cliente,
            cliente_anonimo=cliente_anonimo,
            session_key=request.session.session_key,
            content_type__model='servicio',
            carrito=1,
        )
        if servicios_en_carrito.exists():
            messages.error(request, 'Solo puedes agregar un servicio al carrito.')
            return redirect('carrito')

        content_type = ContentType.objects.get_for_model(Servicio)
    else:
        raise Http404("Tipo no válido")

    # Buscar si el ítem ya está en el carrito
    carrito_item = Carrito.objects.filter(
        cliente=cliente,
        cliente_anonimo=cliente_anonimo,
        session_key=request.session.session_key,
        content_type=content_type,
        object_id=id,
        carrito=1,
    ).first()

    # Si ya existe en el carrito, modificar la cantidad
    if carrito_item:
        if tipo == 'producto' and item.categoria == "Vehículo":
            messages.warning(request, 'El vehículo ya está en el carrito y no se puede modificar la cantidad.')
        else:
            carrito_item.cantidad += cantidad
            carrito_item.save()
    else:
        # Agregar nuevo ítem al carrito
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

def carrito(request):
    """
    Muestra el contenido actual del carrito y gestiona la información de los clientes no registrados.
    """
    cliente = None
    cliente_form = None
    carrito_items = None
    session_key = request.session.session_key
    contiene_servicios = False  # Bandera para identificar si hay servicios en el carrito

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

    # Procesa cada elemento del carrito
    for item in carrito_items:
        item.precio_formateado = formato_precio(item.item.precio)
        item.precio_total_formateado = formato_precio(item.obtener_precio_total())
        
        # Calcular el precio unitario y formatearlo
        item.precio_unitario = formato_precio(item.obtener_precio_total() // item.cantidad)

        # Determina si es un servicio comparando el modelo del item
        is_servicio = item.content_type.model == "servicio"
        item.es_servicio = is_servicio

        # Actualiza la bandera si se encuentra un servicio
        if is_servicio:
            contiene_servicios = True

    # Guarda el estado de contiene_servicios en la sesión
    request.session['contiene_servicios'] = contiene_servicios
    print(f"Contiene servicios guardado en sesión: {contiene_servicios}")

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
        'cliente_form': cliente_form,
        'contiene_servicios': contiene_servicios  # Pasa la bandera a la plantilla
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
