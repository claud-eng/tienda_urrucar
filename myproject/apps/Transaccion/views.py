import calendar
import datetime
import json
import locale
import os
import requests
import time
import uuid
from apps.Usuario.models import Cliente
from calendar import monthrange
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q, Count
from email.headerregistry import ContentTypeHeader
from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import Transaction
from .context_processors import formato_precio
from .forms import ProductoForm, ServicioForm, OrdenDeVentaForm, DetalleOrdenVentaFormset, DetalleOrdenVentaServicioFormset
from .functions import *

@login_required
def listar_productos(request):
    # Obtener todos los productos
    productos = Producto.objects.all()

    # Obtener los valores de los filtros desde la URL
    nombre_query = request.GET.get('nombre')
    stock_query = request.GET.get('stock')
    categoria_filter = request.GET.get('categoria')
    marca_query = request.GET.get('marca')
    sort_order = request.GET.get('sort')

    # Inicializar una consulta vacía
    query = Q()

    # Aplicar los filtros según las selecciones del usuario
    if nombre_query:
        query &= Q(nombre__icontains=nombre_query)

    if categoria_filter:
        query &= Q(categoria=categoria_filter)

    if marca_query:
        query &= Q(marca__icontains=marca_query)

    # Construir una lista de órdenes de ordenamiento para aplicar al final
    sort_orders = []

    if sort_order == 'asc':
        sort_orders.append('precio')
    elif sort_order == 'desc':
        sort_orders.append('-precio')

    if stock_query == 'asc':
        sort_orders.append('cantidad_stock')
    elif stock_query == 'desc':
        sort_orders.append('-cantidad_stock')

    # Aplicar los filtros y ordenamiento en un solo paso
    productos = productos.filter(query).order_by(*sort_orders)

    # Configurar la paginación
    paginator = Paginator(productos, 5)
    page = request.GET.get('page')

    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    # Formatear el precio de cada producto
    for producto in productos:
        producto.precio_formateado = formato_precio(producto.precio)

    # Agregar una variable de contexto para indicar si se ha realizado una búsqueda
    has_search_query_nombre = bool(nombre_query)

    return render(request, 'Transaccion/listar_productos.html', {
        'productos': productos,
        'has_search_query_nombre': has_search_query_nombre,
    })

@login_required
def agregar_producto(request):
    # Vista para agregar un nuevo producto desde un formulario

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)  # Asegúrate de incluir request.FILES para manejar la imagen
        if form.is_valid():
            producto = form.save(commit=False)  # Guarda el formulario sin guardar en la base de datos
            producto.imagen = form.cleaned_data['imagen']  # Asigna la imagen del formulario al producto
            producto.save()  # Guarda el producto en la base de datos
            messages.success(request, 'Producto agregado con éxito.')  # Agrega mensaje de éxito
            return redirect('listar_productos')  # Redirige a la lista de productos después de agregar uno nuevo
    else:
        form = ProductoForm()
    return render(request, "Transaccion/agregar_producto.html", {'form': form})

@login_required
def editar_producto(request, producto_id):
    # Vista para editar la información de un producto existente

    instancia = Producto.objects.get(id=producto_id)

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=instancia)
        if form.is_valid():
            producto = form.save(commit=False)  # Guarda el formulario sin guardar en la base de datos
            if 'imagen' in request.FILES:
                producto.imagen = form.cleaned_data['imagen']  # Asigna la nueva imagen del formulario al producto
            producto.save()  # Guarda el producto en la base de datos

            messages.success(request, 'Producto editado con éxito.')
            return redirect('listar_productos')
    else:
        form = ProductoForm(instance=instancia)

    return render(request, "Transaccion/editar_producto.html", {'form': form})

@login_required
def confirmar_borrar_producto(request, producto_id):
    # Vista para confirmar la eliminación de un producto

    producto = Producto.objects.get(id=producto_id)
    return render(request, 'Transaccion/confirmar_borrar_producto.html', {'producto': producto})

@login_required
def borrar_producto(request, producto_id):
    # Vista para borrar un producto existente

    try:
        instancia = Producto.objects.get(id=producto_id)
        instancia.delete()
        messages.success(request, 'Producto eliminado con éxito.')  # Agrega mensaje de éxito
    except Producto.DoesNotExist:
        pass  # Manejar la situación en la que el producto no existe

    return redirect('listar_productos')  # Redirige a la lista de productos después de borrar uno

@login_required
def listar_servicios(request):
    # Vista para listar servicios con opciones de búsqueda y paginación

    # Obtener todos los servicios
    servicios = Servicio.objects.all()

    # Obtener el valor de búsqueda del parámetro 'nombre' en la URL
    nombre_query = request.GET.get('nombre')

    # Si se proporcionó un valor de búsqueda de nombre, filtrar servicios por nombre
    if nombre_query:
        servicios = servicios.filter(nombre__icontains=nombre_query)

    # Configurar la paginación
    paginator = Paginator(servicios, 5)  # Mostrar 5 servicios por página
    page = request.GET.get('page')  # Obtener el número de página de la solicitud GET

    try:
        servicios = paginator.page(page)
    except PageNotAnInteger:
        servicios = paginator.page(1)  # Si la página no es un número entero, mostrar la primera página
    except EmptyPage:
        servicios = paginator.page(paginator.num_pages)  # Si la página está fuera de rango, mostrar la última página

    # Agregar una variable de contexto para indicar si se ha realizado una búsqueda
    has_search_query_nombre = bool(nombre_query)

    return render(request, 'Transaccion/listar_servicios.html', {
        'servicios': servicios,
        'has_search_query_nombre': has_search_query_nombre,
    })

@login_required
def agregar_servicio(request):
    # Vista para agregar un nuevo servicio desde un formulario

    if request.method == "POST":
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio agregado con éxito.')  # Agrega mensaje de éxito
            return redirect('listar_servicios')  # Redirige a la lista de servicios después de agregar uno nuevo
    else:
        form = ServicioForm()
    return render(request, "Transaccion/agregar_servicio.html", {'form': form})

@login_required
def editar_servicio(request, servicio_id):
    # Vista para editar la información de un servicio existente

    instancia = Servicio.objects.get(id=servicio_id)

    if request.method == "POST":
        form = ServicioForm(request.POST, instance=instancia)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio editado con éxito.')
            return redirect('listar_servicios')
    else:
        form = ServicioForm(instance=instancia)

    return render(request, "Transaccion/editar_servicio.html", {'form': form})

@login_required
def confirmar_borrar_servicio(request, servicio_id):
    # Vista para confirmar la eliminación de un servicio

    servicio = Servicio.objects.get(id=servicio_id)
    return render(request, 'Transaccion/confirmar_borrar_servicio.html', {'servicio': servicio})

@login_required
def borrar_servicio(request, servicio_id):
    # Vista para borrar un servicio existente

    try:
        instancia = Servicio.objects.get(id=servicio_id)
        instancia.delete()
        messages.success(request, 'Servicio eliminado con éxito.')  # Agrega mensaje de éxito
    except Servicio.DoesNotExist:
        pass  # Manejar la situación en la que el servicio no existe

    return redirect('listar_servicios')  # Redirige a la lista de servicios después de borrar uno

@login_required
def gestionar_inventario(request):
    # Aquí puedes agregar la lógica para gestionar el inventario
    return render(request, 'Transaccion/gestionar_inventario.html')

def catalogo_productos(request):
    # Recupera la selección de orden del parámetro 'sort' en la URL
    sort_order = request.GET.get('sort', '')
    categoria_filter = request.GET.get('categoria', '')

    # Recupera todos los productos desde la base de datos
    productos = Producto.objects.all()

    # Aplica el filtro por categoría
    if categoria_filter:
        productos = productos.filter(categoria=categoria_filter)

    # Ordena los productos según la selección del usuario
    if sort_order == 'asc':
        productos = productos.order_by('precio')
    elif sort_order == 'desc':
        productos = productos.order_by('-precio')

    # Configura la paginación (muestra 10 productos por página)
    paginator = Paginator(productos, 10)
    page = request.GET.get('page')

    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    # Aplica el formato de precio y lo guarda en un nuevo atributo
    for producto in productos:
        producto.precio_formateado = formato_precio(producto.precio)

    # Pasa los productos formateados y paginados a la plantilla
    return render(request, 'Transaccion/catalogo_productos.html', {'productos': productos})

def catalogo_servicios(request):
    # Recupera todos los servicios desde la base de datos
    servicios = Servicio.objects.all()
    
    # Configura la ubicación para usar comas como separadores de miles
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

    # Formatea los precios de los servicios
    for servicio in servicios:
        servicio.precio = locale.format_string('%.0f', servicio.precio, grouping=True)

    # Pasa los servicios formateados a la plantilla
    return render(request, 'Transaccion/catalogo_servicios.html', {'servicios': servicios})

def ver_detalles_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    producto.precio_formateado = formato_precio(producto.precio)

    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))

        if cantidad <= 0 or cantidad > producto.cantidad_stock:
            return render(request, 'Transaccion/ver_detalles_producto.html', {
                'producto': producto,
                'error_message': 'Cantidad no válida',
            })

        # Obtén la instancia de Cliente
        cliente = Cliente.objects.get(user=request.user)

        carrito_item = Carrito.objects.filter(cliente=cliente, content_type=ContentType.objects.get_for_model(Producto), object_id=producto.id, carrito=1).first()

        if carrito_item:
            # Si el producto ya está en el carrito, actualiza la cantidad
            carrito_item.cantidad += cantidad
            carrito_item.save()
        else:
            # Si no está en el carrito, crea un nuevo registro
            carrito_item = Carrito(
                cliente=cliente,  # Usa la instancia de Cliente
                content_type=ContentType.objects.get_for_model(Producto),
                object_id=producto.id,
                cantidad=cantidad,
                carrito=1
            )
            carrito_item.save()
        
        return redirect('carrito')

    return render(request, 'Transaccion/ver_detalles_producto.html', {'producto': producto})

def agregar_al_carrito(request, id, tipo):
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

    # Verifica si el producto o servicio ya está en el carrito del usuario
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
            cliente=cliente,  # Usa la instancia de Cliente
            content_type=content_type,
            object_id=id,
            cantidad=cantidad,
            carrito=1
        )
        carrito_item.save()

    return redirect('carrito')

def carrito(request):
    # Obtén la instancia de Cliente asociada con el usuario actual
    cliente = Cliente.objects.get(user=request.user)

    # Filtra los carritos por el cliente, no por el usuario
    carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)

    # Calcula y formatea el precio total del carrito
    total = sum(item.obtener_precio_total() for item in carrito_items)
    total_formateado = formato_precio(total)

    # Agregar información adicional y formatear precios para cada elemento en el carrito
    for item in carrito_items:
        # Formatea el precio del producto/servicio individual
        item.precio_formateado = formato_precio(item.item.precio)
        item.precio_total_formateado = formato_precio(item.obtener_precio_total())
        # Verifica si es un servicio o producto
        item.es_servicio = isinstance(item.item, Servicio)

    return render(request, 'Transaccion/carrito.html', {
        'carrito_items': carrito_items,
        'total': total_formateado
    })

def realizar_compra(request):
    # Tu lógica para procesar la compra aquí
    return render(request, 'Transaccion/realizar_compra.html')

def eliminar_del_carrito(request, item_id):
    cliente = Cliente.objects.get(user=request.user)

    carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()

    if carrito_item is not None:
        # El elemento existe, elimínalo
        carrito_item.delete()
    else:
        # El elemento no existe, puedes manejar esta situación como desees, por ejemplo, mostrar un mensaje de error o redirigir a una página de error.
        raise Http404("El elemento que intentas eliminar no existe o no te pertenece")

    # Redirige de nuevo a la vista del carrito
    return redirect('carrito')

def vaciar_carrito(request):
    cliente = Cliente.objects.get(user=request.user)

    carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
    
    # Elimina todos los elementos del carrito
    carrito_items.delete()

    # Redirige de nuevo a la vista del carrito
    return redirect('carrito')

def aumentar_cantidad(request, item_id):
    cliente = Cliente.objects.get(user=request.user)

    carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()

    if carrito_item:
        carrito_item.cantidad += 1
        carrito_item.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def disminuir_cantidad(request, item_id):
    cliente = Cliente.objects.get(user=request.user)

    carrito_item = Carrito.objects.filter(id=item_id, cliente=cliente, carrito=1).first()

    if carrito_item and carrito_item.cantidad > 1:
        carrito_item.cantidad -= 1
        carrito_item.save()

    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@transaction.atomic
def crear_orden_de_compra(usuario, carrito_items, total):
    """
    Esta función crea una orden de compra en la base de datos y asocia los
    elementos del carrito a dicha orden.

    :param usuario: El usuario que está realizando la compra
    :param carrito_items: Los ítems en el carrito de compras
    :param total: El monto total de la orden
    :return: La instancia de la orden de compra creada
    """
    cliente = Cliente.objects.get(user=usuario)
    # Crear la orden de compra
    orden = OrdenDeCompra.objects.create(cliente=cliente, total=total)
    
    # Asociar los elementos del carrito a la orden de compra
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
        
        DetalleOrdenCompra.objects.create(**detalle_orden_kwargs)
    
    # Luego de crear la orden, marcamos los elementos del carrito como comprados
    carrito_items.update(carrito=0)  # Suponiendo que carrito=0 signifique que los ítems fueron comprados

    return orden

def iniciar_transaccion(request):
    cliente = Cliente.objects.get(user=request.user)

    carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
    total = sum(item.obtener_precio_total() for item in carrito_items)

    # Verifica si el carrito está vacío (total es 0)
    if total == 0:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('carrito')

    # Valores para el entorno de integración (pruebas)
    commerce_code = '597055555532'
    api_key = '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C'

    tx = Transaction(WebpayOptions(commerce_code, api_key, IntegrationType.TEST))

    # Generar un buy_order único dentro del límite de longitud
    timestamp = int(time.time())
    short_uuid = uuid.uuid4().hex[:10]  # toma solo los primeros 10 caracteres
    buy_order = f"{timestamp}{short_uuid}"

    if len(buy_order) > 26:
        buy_order = buy_order[:26]  # asegurarse de que no exceda los 26 caracteres

    session_id = request.session.session_key or 'session-unknown'
    amount = total
    return_url = request.build_absolute_uri('/transaccion/transaccion_finalizada/')

    try:
        response = tx.create(buy_order, session_id, amount, return_url)
        if 'url' in response and 'token' in response:
            return redirect(response['url'] + "?token_ws=" + response['token'])
        else:
            return HttpResponse("Error: la respuesta de Transbank no contiene URL o token")
    except TransbankError as e:
        print(e.message)
        return HttpResponse("Error al crear la transacción: " + str(e.message))

def transaccion_finalizada(request):
    token_ws = request.GET.get('token_ws')
    cliente = Cliente.objects.get(user=request.user)

    commerce_code = '597055555532'
    api_key = '579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C'
    tx = Transaction(WebpayOptions(commerce_code, api_key, IntegrationType.TEST))

    try:
        response = tx.commit(token_ws)
        contexto = {}

        # Usar get_or_create para la orden
        orden, created = OrdenDeCompra.objects.get_or_create(
            token_ws=token_ws,
            defaults={
                'cliente': cliente,
                'total': response.get('amount', 0),
                'estado': 'pendiente',
                'fecha': timezone.now(),
                'numero_orden': response.get('buy_order'),
                'tipo_pago': response.get('payment_type_code', None),
                'monto_cuotas': response.get('installments_amount', None),
                'numero_cuotas': response.get('installments_number', None)
            }
        )

        if not created:
            contexto['mensaje_error'] = "Esta transacción ya ha sido procesada."
            contexto['orden'] = orden
            contexto['orden'].total_formateado = formato_precio(orden.total)  # Formato para orden total
            return render(request, 'Transaccion/retorno_webpay.html', contexto)

        detalles_compra = []
        transaccion_exitosa = False

        if response.get('status') == 'AUTHORIZED':
            transaccion_exitosa = True
            carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
            stock_insuficiente = False

            for item in carrito_items:
                if isinstance(item.item, Producto) and item.item.cantidad_stock < item.cantidad:
                    stock_insuficiente = True
                    break

            if stock_insuficiente:
                orden.estado = 'rechazada'
                contexto['mensaje_error'] = "Stock insuficiente para uno o más productos."
                orden.save()
                return render(request, 'Transaccion/retorno_webpay.html', contexto)
            else:
                orden.estado = 'aprobada'
                for item in carrito_items:
                    detalle = {
                        'nombre': item.item.nombre,
                        'cantidad': item.cantidad,
                        'precio_unitario': formato_precio(item.item.precio),  # Formato para precio unitario
                        'precio_total': formato_precio(item.obtener_precio_total())  # Formato para precio total
                    }
                    detalles_compra.append(detalle)

                    if isinstance(item.item, Producto):
                        producto = item.item
                        producto.cantidad_stock -= item.cantidad
                        producto.save()

                    DetalleOrdenCompra.objects.create(
                        orden_compra=orden,
                        producto=item.item if isinstance(item.item, Producto) else None,
                        servicio=item.item if isinstance(item.item, Servicio) else None,
                        precio=item.obtener_precio_total(),
                        cantidad=item.cantidad
                    )

                carrito_items.update(carrito=0)

        else:
            orden.estado = 'rechazada'
            contexto['mensaje_error'] = "Transacción rechazada por el banco"

        orden.save()

        # Formato de total de orden para el contexto
        contexto['orden'] = orden
        contexto['orden'].total_formateado = formato_precio(orden.total)
        contexto['transaccion_exitosa'] = transaccion_exitosa
        contexto['detalles_compra'] = detalles_compra

        # Enviar correo electrónico con comprobante de pago si la transacción es exitosa
        if transaccion_exitosa:
            buffer_pdf = generar_comprobante_pdf_correo(orden)

            email_subject = "Comprobante de Pago - Orden {}".format(orden.numero_orden)
            email_body = "Aquí está su comprobante de pago para la orden {}.".format(orden.numero_orden)
            email = EmailMessage(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [cliente.user.email]
            )

            email.attach('comprobante_orden_{}.pdf'.format(orden.numero_orden), buffer_pdf.getvalue(), 'application/pdf')

            email.send()

        return render(request, 'Transaccion/retorno_webpay.html', contexto)

    except TransbankError as e:
        return HttpResponse(f"Error al procesar la transacción: {e.message}")

def listar_ventas_online(request):
    cliente_query = request.GET.get('cliente', '')

    query = Q()
    query &= Q(estado='aprobada')

    if hasattr(request.user, 'cliente'):
        query &= Q(cliente=request.user.cliente)
    elif hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador':
        if cliente_query:
            query &= Q(cliente__user__username__icontains=cliente_query)
    else:
        return redirect('home')

    ordenes_compra = OrdenDeCompra.objects.filter(query).order_by('fecha')

    paginator = Paginator(ordenes_compra, 5)
    page = request.GET.get('page')

    try:
        ordenes_paginadas = paginator.page(page)
    except PageNotAnInteger:
        ordenes_paginadas = paginator.page(1)
    except EmptyPage:
        ordenes_paginadas = paginator.page(paginator.num_pages)

    # Formatear el total de cada orden y construir una lista de detalles con precios formateados
    for orden in ordenes_paginadas:
        orden.total_formateado = formato_precio(orden.total)
        detalles_formateados = []
        
        for detalle in orden.detalleordencompra_set.all():
            detalles_formateados.append({
                'nombre': detalle.producto.nombre if detalle.producto else detalle.servicio.nombre,
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(detalle.precio),
                'es_producto': bool(detalle.producto),
            })

        # Agrega la lista de detalles formateados a la orden
        orden.detalles_formateados = detalles_formateados

    context = {
        'ordenes_paginadas': ordenes_paginadas,
        'cliente_query': cliente_query,
        'es_administrador': hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador'
    }

    return render(request, 'Transaccion/listar_ventas_online.html', context)

def agregar_venta(request):
    orden_venta_form = OrdenDeVentaForm(request.POST or None)
    detalle_formset = DetalleOrdenVentaFormset(request.POST or None, prefix='productos')
    detalle_servicio_formset = DetalleOrdenVentaServicioFormset(request.POST or None, prefix='servicios')
    query_string = request.GET.urlencode()

    if request.method == 'POST':
        if orden_venta_form.is_valid() and detalle_formset.is_valid() and detalle_servicio_formset.is_valid():

            cliente = orden_venta_form.cleaned_data.get('cliente')
            # Verifica si el ID del cliente es 1
            if cliente.id == 1:
                # Verifica si hay servicios intentando ser comprados
                if any(form.cleaned_data for form in detalle_servicio_formset):
                    messages.error(request, 'Este cliente no puede comprar servicios.')
                    return render(request, 'Transaccion/agregar_venta.html', {
                        'orden_venta_form': orden_venta_form,
                        'detalle_formset': detalle_formset,
                        'detalle_servicio_formset': detalle_servicio_formset,
                        'query_string': query_string,
                    })
                
            # Calculamos el total de productos
            total_productos = sum(form.cleaned_data.get('cantidad', 0) * form.cleaned_data.get('producto').precio for form in detalle_formset if form.cleaned_data.get('producto'))

            # Calculamos el total de servicios
            total_servicios = sum(form.cleaned_data.get('servicio').precio for form in detalle_servicio_formset if form.cleaned_data.get('servicio'))

            # Sumamos ambos totales
            total_venta = total_productos + total_servicios

            # Obtenemos el pago del cliente
            pago_cliente = orden_venta_form.cleaned_data.get('pago_cliente')

            # Comprobamos si el pago del cliente es suficiente
            if pago_cliente < total_venta:
                messages.error(request, 'La cantidad ingresada a pagar es inferior al total de la venta.')
                return render(request, 'Transaccion/agregar_venta.html', {
                    'orden_venta_form': orden_venta_form,
                    'detalle_formset': detalle_formset,
                    'detalle_servicio_formset': detalle_servicio_formset,
                    'query_string': query_string,
                })

            # Aseguramos que el stock es suficiente
            stock_insuficiente = False
            for form in detalle_formset:
                if form.cleaned_data.get('producto'):
                    producto = form.cleaned_data['producto']
                    cantidad = form.cleaned_data['cantidad']
                    if cantidad > producto.cantidad_stock:
                        stock_insuficiente = True
                        messages.error(request, f'Stock insuficiente para el producto {producto.nombre}.')
                        break

            if stock_insuficiente:
                return render(request, 'Transaccion/agregar_venta.html', {
                    'orden_venta_form': orden_venta_form,
                    'detalle_formset': detalle_formset,
                    'detalle_servicio_formset': detalle_servicio_formset,
                    'query_string': query_string,
                })

            with transaction.atomic():
                # Creamos y guardamos la instancia de orden de venta
                orden_venta = orden_venta_form.save(commit=False)
                orden_venta.total = total_venta
                orden_venta.cambio = max(pago_cliente - total_venta, 0)
                orden_venta.save()

                # Actualizamos el stock y guardamos detalles de productos
                for form in detalle_formset:
                    if form.cleaned_data.get('producto'):
                        producto = form.cleaned_data['producto']
                        cantidad = form.cleaned_data['cantidad']
                        producto.cantidad_stock -= cantidad
                        producto.save()

                        detalle = form.save(commit=False)
                        detalle.orden_venta = orden_venta
                        detalle.save()

                # Guardamos detalles de servicios
                for form in detalle_servicio_formset:
                    if form.cleaned_data.get('servicio'):
                        detalle = form.save(commit=False)
                        detalle.orden_venta = orden_venta
                        detalle.save()

                messages.success(request, 'Venta registrada exitosamente.')
                return redirect('listar_ventas')

        else:
            messages.error(request, 'Errores en el formulario de venta')

    context = {
        'orden_venta_form': orden_venta_form,
        'detalle_formset': detalle_formset,
        'detalle_servicio_formset': detalle_servicio_formset,
        'query_string': query_string,
    }
    return render(request, 'Transaccion/agregar_venta.html', context)

def listar_ventas(request):
    # Obtener el valor de búsqueda del cliente desde la URL
    cliente_query = request.GET.get('cliente', '')

    # Inicializar una consulta vacía
    query = Q()

    # Si el usuario es un cliente, solo muestra sus ventas
    if hasattr(request.user, 'cliente'):
        query &= Q(cliente=request.user.cliente)
    elif hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador':
        if cliente_query:
            query &= Q(cliente__user__username__icontains=cliente_query)
    else:
        # Redireccionar a otra página si el usuario no tiene permiso
        return redirect('home')

    # Filtrar las ventas según la consulta construida
    ventas_filtradas = OrdenDeVenta.objects.filter(query).order_by('id')

    # Configurar la paginación
    paginator = Paginator(ventas_filtradas, 5)  # Mostrar 5 ventas por página
    page = request.GET.get('page')

    try:
        ventas_paginadas = paginator.page(page)
    except PageNotAnInteger:
        ventas_paginadas = paginator.page(1)
    except EmptyPage:
        ventas_paginadas = paginator.page(paginator.num_pages)

    ventas_list = []
    for venta in ventas_paginadas:
        productos = venta.detalleordenventa_set.filter(producto__isnull=False)
        servicios = venta.detalleordenventa_set.filter(servicio__isnull=False)
        # Agregar la información de productos y servicios al contexto de la plantilla
        ventas_list.append({
            'venta': venta,
            'productos': productos,
            'servicios': servicios,
            'tiene_productos': productos.exists(),
            'tiene_servicios': servicios.exists(),
        })

    return render(request, 'Transaccion/listar_ventas.html', {
        'ventas_list': ventas_list,
        'ventas_paginadas': ventas_paginadas,
        'cliente_query': cliente_query,  # Agregamos esta línea para utilizarla en la plantilla HTML
    })

@login_required
def gestionar_transacciones(request):
    return render(request, 'Transaccion/gestionar_transacciones.html')

def reportes_ventas(request):
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month

    anio = int(request.GET.get('anio', anio_actual))
    mes = int(request.GET.get('mes', mes_actual))

    top_cinco_productos = top_cinco_productos_vendidos(anio, mes)
    top_cinco_servicios = top_cinco_servicios_vendidos(anio, mes)

    mensaje_productos = ""
    mensaje_servicios = ""

    if not top_cinco_productos:
        mensaje_productos = "No se han registrado ventas de productos en el mes seleccionado."

    if not top_cinco_servicios:
        mensaje_servicios = "No se han registrado ventas de servicios en el mes seleccionado."

    datos_productos = json.dumps({
        'labels': [producto.nombre for producto in top_cinco_productos],
        'data': [producto.total_vendido for producto in top_cinco_productos]
    }, cls=DjangoJSONEncoder) if top_cinco_productos else json.dumps({})

    datos_servicios = json.dumps({
        'labels': [servicio.nombre for servicio in top_cinco_servicios],
        'data': [servicio.total_vendido for servicio in top_cinco_servicios]
    }, cls=DjangoJSONEncoder) if top_cinco_servicios else json.dumps({})

    # Diccionario de nombres de meses en español
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    nombre_mes = meses.get(mes, "Mes desconocido")

    datos_grafico = {
        'labels': [producto.nombre for producto in top_cinco_productos],
        'values': [producto.total_vendido for producto in top_cinco_productos]
    }
    imagen_grafico = generar_grafico_base64(datos_grafico)

    contexto = {
        'datos_productos_json': datos_productos,
        'datos_servicios_json': datos_servicios,
        'mensaje_productos': mensaje_productos,
        'mensaje_servicios': mensaje_servicios,
        'rango_anios': range(2022, 2028),
        'rango_meses': range(1, 13),
        'anio_actual': anio_actual,
        'mes_actual': mes_actual,
        'anio_seleccionado': anio,
        'mes_seleccionado': mes,
        'nombre_mes': nombre_mes,
        'imagen_grafico': imagen_grafico,
        'top_cinco_productos': top_cinco_productos,
        'top_cinco_servicios': top_cinco_servicios,
    }

    return render(request, 'Transaccion/reportes_ventas.html', contexto)


