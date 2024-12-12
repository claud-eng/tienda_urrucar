import calendar  # Importa el módulo 'calendar' para manejar calendarios y fechas.
import datetime  # Importa 'datetime' para trabajar con fechas y horas.
import locale  # Importa 'locale' para manejar configuraciones regionales, como formatos de fecha y moneda.
import os  # Importa 'os' para interactuar con el sistema operativo.
import requests  # Importa 'requests' para realizar solicitudes HTTP.
from apps.Usuario.models import Cliente  # Importa el modelo 'Cliente' desde la aplicación 'Usuario'.
from calendar import monthrange  # Importa 'monthrange' para obtener el rango de días en un mes.
from django.conf import settings  # Importa el módulo de configuración de Django.
from django.contrib import messages  # Importa 'messages' para mostrar mensajes a los usuarios en Django.
from django.contrib.auth.decorators import login_required  # Importa 'login_required' para proteger vistas que requieren autenticación.
from django.contrib.contenttypes.models import ContentType  # Importa 'ContentType' para manejar contenido genérico en Django.
from django.core.mail import EmailMessage  # Importa 'EmailMessage' para enviar correos electrónicos.
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage  # Importa 'Paginator' y excepciones para manejar la paginación.
from django.db import transaction  # Importa 'transaction' para manejar transacciones de base de datos.
from django.db.models import Q, Count  # Importa 'Q' y 'Count' para construir consultas complejas.
from email.headerregistry import ContentTypeHeader  # Importa 'ContentTypeHeader' para manipular encabezados de correo electrónico.
from .context_processors import formato_precio  # Importa 'formato_precio' para formatear precios en contextos de plantilla.
from .forms import ProductoForm, ServicioForm, DetalleVentaOnline, VentaOnlineForm, VentaManualForm, DetalleVentaOnlineFormset, DetalleVentaManualFormset, DetalleVentaManualServicioFormset  # Importa formularios para gestionar productos, servicios y ventas.
from .functions import *  # Importa todas las funciones definidas en 'functions' del directorio actual.

@login_required
def listar_productos(request):
    """
    Lista todos los productos en la base de datos con opciones de filtrado,
    ordenamiento y paginación. Permite buscar por nombre, categoría, marca
    y stock.
    """
    productos = Producto.objects.all()
    nombre_query = request.GET.get('nombre')
    stock_query = request.GET.get('stock')
    categoria_filter = request.GET.get('categoria')
    marca_query = request.GET.get('marca')
    sort_order = request.GET.get('sort')

    query = Q()

    if nombre_query:
        query &= Q(nombre__icontains=nombre_query)
    if categoria_filter:
        query &= Q(categoria=categoria_filter)
    if marca_query:
        query &= Q(marca__icontains=marca_query)

    sort_orders = []
    if sort_order == 'asc':
        sort_orders.append('precio')
    elif sort_order == 'desc':
        sort_orders.append('-precio')
    if stock_query == 'asc':
        sort_orders.append('cantidad_stock')
    elif stock_query == 'desc':
        sort_orders.append('-cantidad_stock')

    productos = productos.filter(query).order_by(*sort_orders)

    paginator = Paginator(productos, 5)
    page = request.GET.get('page')

    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    for producto in productos:
        producto.precio_formateado = formato_precio(producto.precio)
        if producto.precio_reserva:  # Solo formatea si el precio de reserva no es nulo
            producto.precio_reserva_formateado = formato_precio(producto.precio_reserva)
        else:
            producto.precio_reserva_formateado = None

    has_search_query_nombre = bool(nombre_query)

    return render(request, 'Transaccion/listar_productos.html', {
        'productos': productos,
        'has_search_query_nombre': has_search_query_nombre,
    })

@login_required
def agregar_producto(request):
    """
    Agrega un nuevo producto a la base de datos mediante un formulario.
    Permite cargar una imagen para el producto.
    """
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.imagen = form.cleaned_data['imagen']
            producto.save()
            messages.success(request, 'Producto agregado con éxito.')
            return redirect('listar_productos')
    else:
        form = ProductoForm()
    return render(request, "Transaccion/agregar_producto.html", {'form': form})

@login_required
def editar_producto(request, producto_id):
    """
    Edita la información de un producto existente, permitiendo actualizar
    sus datos e imagen.
    """
    instancia = Producto.objects.get(id=producto_id)

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=instancia)
        if form.is_valid():
            producto = form.save(commit=False)
            if 'imagen' in request.FILES:
                producto.imagen = form.cleaned_data['imagen']
            producto.save()
            messages.success(request, 'Producto editado con éxito.')
            return redirect('listar_productos')
    else:
        form = ProductoForm(instance=instancia)

    return render(request, "Transaccion/editar_producto.html", {'form': form})

@login_required
def confirmar_borrar_producto(request, producto_id):
    """
    Confirma la eliminación de un producto mostrando una página de confirmación.
    """
    producto = Producto.objects.get(id=producto_id)
    return render(request, 'Transaccion/confirmar_borrar_producto.html', {'producto': producto})

@login_required
def borrar_producto(request, producto_id):
    """
    Elimina un producto de la base de datos y redirige a la lista de productos.
    """
    try:
        instancia = Producto.objects.get(id=producto_id)
        instancia.delete()
        messages.success(request, 'Producto eliminado con éxito.')
    except Producto.DoesNotExist:
        pass

    return redirect('listar_productos')

@login_required
def listar_servicios(request):
    """
    Lista todos los servicios en la base de datos con opciones de búsqueda
    y paginación.
    """
    servicios = Servicio.objects.all()
    nombre_query = request.GET.get('nombre')

    if nombre_query:
        servicios = servicios.filter(nombre__icontains=nombre_query)

    paginator = Paginator(servicios, 5)
    page = request.GET.get('page')

    try:
        servicios = paginator.page(page)
    except PageNotAnInteger:
        servicios = paginator.page(1)
    except EmptyPage:
        servicios = paginator.page(paginator.num_pages)

    has_search_query_nombre = bool(nombre_query)

    return render(request, 'Transaccion/listar_servicios.html', {
        'servicios': servicios,
        'has_search_query_nombre': has_search_query_nombre,
    })

@login_required
def agregar_servicio(request):
    """
    Agrega un nuevo servicio a la base de datos mediante un formulario.
    """
    if request.method == "POST":
        form = ServicioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servicio agregado con éxito.')
            return redirect('listar_servicios')
    else:
        form = ServicioForm()
    return render(request, "Transaccion/agregar_servicio.html", {'form': form})

@login_required
def editar_servicio(request, servicio_id):
    """
    Edita la información de un servicio existente en la base de datos.
    """
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
    """
    Muestra una página de confirmación antes de eliminar un servicio.
    """
    servicio = Servicio.objects.get(id=servicio_id)
    return render(request, 'Transaccion/confirmar_borrar_servicio.html', {'servicio': servicio})

@login_required
def borrar_servicio(request, servicio_id):
    """
    Elimina un servicio de la base de datos y redirige a la lista de servicios.
    """
    try:
        instancia = Servicio.objects.get(id=servicio_id)
        instancia.delete()
        messages.success(request, 'Servicio eliminado con éxito.')
    except Servicio.DoesNotExist:
        pass

    return redirect('listar_servicios')

@login_required
def gestionar_inventario(request):
    """
    Permite al administrador gestionar el inventario de productos y servicios.
    """
    return render(request, 'Transaccion/gestionar_inventario.html')

def catalogo_productos(request):
    """
    Muestra un catálogo de productos, permitiendo ordenar por precio y
    filtrar por categoría. La vista también incluye paginación.
    """
    sort_order = request.GET.get('sort', '')
    categoria_filter = request.GET.get('categoria', '')

    productos = Producto.objects.all()

    if categoria_filter:
        productos = productos.filter(categoria=categoria_filter)

    if sort_order == 'asc':
        productos = productos.order_by('precio')
    elif sort_order == 'desc':
        productos = productos.order_by('-precio')

    paginator = Paginator(productos, 10)
    page = request.GET.get('page')

    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    for producto in productos:
        producto.precio_formateado = formato_precio(producto.precio)

    return render(request, 'Transaccion/catalogo_productos.html', {'productos': productos})

def catalogo_servicios(request):
    """
    Muestra un catálogo de servicios con precios formateados.
    """
    servicios = Servicio.objects.all()
    
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')

    for servicio in servicios:
        servicio.precio = locale.format_string('%.0f', servicio.precio, grouping=True)

    return render(request, 'Transaccion/catalogo_servicios.html', {'servicios': servicios})

def listar_ventas_online(request):
    """
    Lista todas las ventas aprobadas, con opciones de búsqueda por cliente.
    Los detalles de la venta incluyen el precio total formateado y una lista
    de productos y servicios vendidos.
    """
    cliente_query = request.GET.get('cliente', '')

    query = Q(estado='aprobada')
    if hasattr(request.user, 'cliente'):
        query &= Q(cliente=request.user.cliente)
    elif hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador':
        if cliente_query:
            query &= Q(cliente__user__username__icontains=cliente_query)
    else:
        return redirect('home')

    ordenes_compra = VentaOnline.objects.filter(query).order_by('fecha')

    paginator = Paginator(ordenes_compra, 5)
    page = request.GET.get('page')

    try:
        ordenes_paginadas = paginator.page(page)
    except PageNotAnInteger:
        ordenes_paginadas = paginator.page(1)
    except EmptyPage:
        ordenes_paginadas = paginator.page(paginator.num_pages)

    for orden in ordenes_paginadas:
        orden.total_formateado = formato_precio(orden.total)
        detalles_formateados = []
        
        for detalle in orden.detalleventaonline_set.all():
            detalles_formateados.append({
                'nombre': detalle.producto.nombre if detalle.producto else detalle.servicio.nombre,
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(detalle.precio),
                'es_producto': bool(detalle.producto),
            })

        orden.detalles_formateados = detalles_formateados

    context = {
        'ordenes_paginadas': ordenes_paginadas,
        'cliente_query': cliente_query,
        'es_administrador': hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador'
    }

    return render(request, 'Transaccion/listar_ventas_online.html', context)

@login_required
def editar_venta_online(request, venta_id):
    """
    Permite editar únicamente el estado de la reserva de los productos de la categoría 'Vehículo'
    en una venta online específica.
    """
    venta = get_object_or_404(VentaOnline, id=venta_id)

    if request.method == "POST":
        # Iterar por cada detalle de la venta
        for detalle in venta.detalleventaonline_set.all():
            if detalle.producto and detalle.producto.categoria == "Vehículo":
                nuevo_estado = request.POST.get(f"estado_reserva_{detalle.id}")
                if nuevo_estado in ['En proceso', 'Vendida', 'Desistida']:
                    detalle.estado_reserva = nuevo_estado
                    detalle.save()
        messages.success(request, "Estado de la reserva actualizado correctamente.")
        return redirect("listar_ventas_online")

    # Renderizar formulario de edición
    detalles = []
    for detalle in venta.detalleventaonline_set.all():
        if detalle.producto and detalle.producto.categoria == "Vehículo":
            detalles.append({
                'detalle_id': detalle.id,
                'producto_nombre': detalle.producto.nombre,
                'estado_reserva': detalle.estado_reserva
            })

    return render(request, "Transaccion/editar_venta_online.html", {
        'venta': venta,
        'detalles': detalles
    })

def agregar_venta(request):
    """
    Permite agregar una nueva venta, verificando la disponibilidad de stock
    y los permisos del cliente. Calcula el total y maneja pagos y cambios.
    """
    orden_venta_form = VentaManualForm(request.POST or None)
    detalle_formset = DetalleVentaManualFormset(request.POST or None, prefix='productos')
    detalle_servicio_formset = DetalleVentaManualServicioFormset(request.POST or None, prefix='servicios')
    query_string = request.GET.urlencode()

    if request.method == 'POST':
        if orden_venta_form.is_valid() and detalle_formset.is_valid() and detalle_servicio_formset.is_valid():

            cliente = orden_venta_form.cleaned_data.get('cliente')
            if cliente.id == 1 and any(form.cleaned_data for form in detalle_servicio_formset):
                messages.error(request, 'Este cliente no puede comprar servicios.')
                return render(request, 'Transaccion/agregar_venta.html', {
                    'orden_venta_form': orden_venta_form,
                    'detalle_formset': detalle_formset,
                    'detalle_servicio_formset': detalle_servicio_formset,
                    'query_string': query_string,
                })
                
            total_productos = sum(form.cleaned_data.get('cantidad', 0) * form.cleaned_data.get('producto').precio for form in detalle_formset if form.cleaned_data.get('producto'))
            total_servicios = sum(form.cleaned_data.get('servicio').precio for form in detalle_servicio_formset if form.cleaned_data.get('servicio'))
            total_venta = total_productos + total_servicios
            pago_cliente = orden_venta_form.cleaned_data.get('pago_cliente')

            if pago_cliente < total_venta:
                messages.error(request, 'La cantidad ingresada a pagar es inferior al total de la venta.')
                return render(request, 'Transaccion/agregar_venta.html', {
                    'orden_venta_form': orden_venta_form,
                    'detalle_formset': detalle_formset,
                    'detalle_servicio_formset': detalle_servicio_formset,
                    'query_string': query_string,
                })

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
                orden_venta = orden_venta_form.save(commit=False)
                orden_venta.total = total_venta
                orden_venta.cambio = max(pago_cliente - total_venta, 0)
                orden_venta.save()

                for form in detalle_formset:
                    if form.cleaned_data.get('producto'):
                        producto = form.cleaned_data['producto']
                        cantidad = form.cleaned_data['cantidad']
                        producto.cantidad_stock -= cantidad
                        producto.save()
                        detalle = form.save(commit=False)
                        detalle.orden_venta = orden_venta
                        detalle.save()

                for form in detalle_servicio_formset:
                    if form.cleaned_data.get('servicio'):
                        detalle = form.save(commit=False)
                        detalle.orden_venta = orden_venta
                        detalle.save()

                messages.success(request, 'Venta registrada exitosamente.')
                return redirect('listar_ventas_manuales')

        else:
            messages.error(request, 'Errores en el formulario de venta')

    context = {
        'orden_venta_form': orden_venta_form,
        'detalle_formset': detalle_formset,
        'detalle_servicio_formset': detalle_servicio_formset,
        'query_string': query_string,
    }
    return render(request, 'Transaccion/agregar_venta.html', context)

def listar_ventas_manuales(request):
    """
    Lista todas las ventas registradas de forma manual, con opciones de búsqueda por cliente y paginación.
    Muestra los detalles de productos y servicios para cada venta.
    """
    cliente_query = request.GET.get('cliente', '')
    query = Q()

    if hasattr(request.user, 'cliente'):
        query &= Q(cliente=request.user.cliente)
    elif hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador':
        if cliente_query:
            query &= Q(cliente__user__username__icontains=cliente_query)
    else:
        return redirect('home')

    ventas_filtradas = VentaManual.objects.filter(query).order_by('id')

    paginator = Paginator(ventas_filtradas, 5)
    page = request.GET.get('page')

    try:
        ventas_paginadas = paginator.page(page)
    except PageNotAnInteger:
        ventas_paginadas = paginator.page(1)
    except EmptyPage:
        ventas_paginadas = paginator.page(paginator.num_pages)

    ventas_list = []
    for venta in ventas_paginadas:
        productos = venta.detalleventamanual_set.filter(producto__isnull=False)
        servicios = venta.detalleventamanual_set.filter(servicio__isnull=False)
        ventas_list.append({
            'venta': venta,
            'productos': productos,
            'servicios': servicios,
            'tiene_productos': productos.exists(),
            'tiene_servicios': servicios.exists(),
        })

    return render(request, 'Transaccion/listar_ventas_manuales.html', {
        'ventas_list': ventas_list,
        'ventas_paginadas': ventas_paginadas,
        'cliente_query': cliente_query,
    })

@login_required
def gestionar_transacciones(request):
    """
    Vista para que los administradores gestionen todas las transacciones.
    """
    return render(request, 'Transaccion/gestionar_transacciones.html')


