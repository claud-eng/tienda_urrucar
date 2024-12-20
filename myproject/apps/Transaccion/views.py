import calendar  # Importa el módulo 'calendar' para manejar calendarios y fechas.
import datetime  # Importa 'datetime' para trabajar con fechas y horas.
import locale  # Importa 'locale' para manejar configuraciones regionales, como formatos de fecha y moneda.
import os  # Importa 'os' para interactuar con el sistema operativo.
import requests  # Importa 'requests' para realizar solicitudes HTTP.
from apps.Usuario.models import Cliente  # Importa el modelo 'Cliente' desde la aplicación 'Usuario'.
from calendar import monthrange  # Importa 'monthrange' para obtener el rango de días en un mes.
from collections import Counter  # Importa Counter para contar elementos en iterables.
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
from .models import * # Importa la función ImagenProducto para gestionar la lógica de imágenes adicionales en la galería de productos.

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
# Función para agregar producto
def agregar_producto(request):
    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()

            # Procesar imágenes adicionales
            for imagen in request.FILES.getlist('imagenes'):
                ImagenProducto.objects.create(producto=producto, imagen=imagen)

            messages.success(request, 'Producto y galería de imágenes agregados con éxito.')
            return redirect('listar_productos')
    else:
        form = ProductoForm()

    return render(request, "Transaccion/agregar_producto.html", {'form': form})

@login_required
# Función para editar producto
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    imagenes_adicionales = ImagenProducto.objects.filter(producto=producto)  # Obtén las imágenes adicionales

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save()

            # Eliminar imagen principal si está marcada para eliminación
            imagen_principal_id = request.POST.get("imagen_principal_a_eliminar")
            if imagen_principal_id and producto.imagen:
                # Eliminar la imagen principal
                if os.path.exists(producto.imagen.path):
                    os.remove(producto.imagen.path)  # Elimina físicamente el archivo
                producto.imagen.delete(save=False)
                producto.imagen = None
                producto.save()

            imagenes_a_eliminar = request.POST.get("imagenes_a_eliminar", "").split(",")
            for imagen_id in imagenes_a_eliminar:
                if imagen_id.isdigit():
                    try:
                        imagen_obj = ImagenProducto.objects.get(id=imagen_id)
                        if os.path.exists(imagen_obj.imagen.path):
                            os.remove(imagen_obj.imagen.path)  # Elimina físicamente el archivo
                        imagen_obj.delete()  # Elimina de la base de datos
                    except ImagenProducto.DoesNotExist:
                        pass

            # Procesar nuevas imágenes adicionales
            for imagen in request.FILES.getlist("imagenes"):
                ImagenProducto.objects.create(producto=producto, imagen=imagen)

            messages.success(request, "Producto actualizado con éxito.")
            return redirect("listar_productos")
    else:
        form = ProductoForm(instance=producto)

    return render(request, "Transaccion/editar_producto.html", {
        "form": form,
        "producto": producto,
        "imagenes_adicionales": imagenes_adicionales,  # Pasa las imágenes adicionales al contexto
    })

@login_required
# Eliminar imagen adicional
def eliminar_imagen_adicional(request, imagen_id):
    imagen = get_object_or_404(ImagenProducto, id=imagen_id)
    if os.path.exists(imagen.imagen.path):
        os.remove(imagen.imagen.path)  # Elimina el archivo físicamente
    imagen.delete()  # Elimina la referencia de la base de datos
    messages.success(request, 'La imagen adicional fue eliminada con éxito.')
    return redirect('editar_producto', producto_id=imagen.producto.id)

@login_required
def confirmar_borrar_producto(request, producto_id):
    """
    Confirma la eliminación de un producto mostrando una página de confirmación.
    """
    producto = Producto.objects.get(id=producto_id)
    return render(request, 'Transaccion/confirmar_borrar_producto.html', {'producto': producto})

@login_required
# Función para borrar producto
def borrar_producto(request, producto_id):
    try:
        producto = Producto.objects.get(id=producto_id)
        
        # Eliminar imagen principal si existe
        if producto.imagen and os.path.exists(producto.imagen.path):
            os.remove(producto.imagen.path)
        
        # Eliminar imágenes adicionales
        for imagen in producto.imagenes.all():
            if os.path.exists(imagen.imagen.path):
                os.remove(imagen.imagen.path)
            imagen.delete()  # Eliminar referencia en la base de datos

        producto.delete()  # Eliminar el producto
        messages.success(request, "Producto eliminado con éxito.")
    except Producto.DoesNotExist:
        messages.error(request, "El producto no existe.")

    return redirect("listar_productos")

@login_required
def listar_servicios(request):
    """
    Lista todos los servicios en la base de datos con opciones de búsqueda
    y paginación.
    """
    servicios = Servicio.objects.all().order_by('id')  # Agrega un orden explícito
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

    # Formatear el precio de cada servicio
    for servicio in servicios:
        servicio.precio_formateado = formato_precio(servicio.precio)

    has_search_query_nombre = bool(nombre_query)

    return render(request, 'Transaccion/listar_servicios.html', {
        'servicios': servicios,
        'has_search_query_nombre': has_search_query_nombre,
    })

@login_required
# Función para agregar servicio
def agregar_servicio(request):
    if request.method == "POST":
        form = ServicioForm(request.POST, request.FILES)
        if form.is_valid():
            servicio = form.save()
            messages.success(request, "Servicio agregado con éxito.")
            return redirect("listar_servicios")
    else:
        form = ServicioForm()
    return render(request, "Transaccion/agregar_servicio.html", {"form": form})

@login_required
# Función para editar servicio
def editar_servicio(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)

    if request.method == "POST":
        form = ServicioForm(request.POST, request.FILES, instance=servicio)

        # Verificar si se marcó la imagen para eliminación
        imagen_a_eliminar = request.POST.get("imagen_a_eliminar")
        if imagen_a_eliminar and servicio.imagen:
            # Eliminar el archivo físicamente
            if os.path.exists(servicio.imagen.path):
                os.remove(servicio.imagen.path)
            # Eliminar referencia en la base de datos
            servicio.imagen.delete(save=False)

        if form.is_valid():
            form.save()
            messages.success(request, "Servicio actualizado con éxito.")
            return redirect("listar_servicios")
    else:
        form = ServicioForm(instance=servicio)

    return render(request, "Transaccion/editar_servicio.html", {"form": form, "servicio": servicio})

@login_required
def confirmar_borrar_servicio(request, servicio_id):
    """
    Muestra una página de confirmación antes de eliminar un servicio.
    """
    servicio = Servicio.objects.get(id=servicio_id)
    return render(request, 'Transaccion/confirmar_borrar_servicio.html', {'servicio': servicio})

@login_required
# Función para editar servicio
def borrar_servicio(request, servicio_id):
    try:
        servicio = Servicio.objects.get(id=servicio_id)
        
        # Eliminar imagen si existe
        if servicio.imagen and os.path.exists(servicio.imagen.path):
            os.remove(servicio.imagen.path)
        
        servicio.delete()  # Eliminar el servicio
        messages.success(request, "Servicio eliminado con éxito.")
    except Servicio.DoesNotExist:
        messages.error(request, "El servicio no existe.")

    return redirect("listar_servicios")

@login_required
def gestionar_inventario(request):
    """
    Permite al administrador gestionar el inventario de productos y servicios.
    """
    return render(request, 'Transaccion/gestionar_inventario.html')

def catalogo_productos(request):
    """
    Muestra un catálogo de productos permitiendo filtrar por marca y ordenar por precio.
    """
    # Obtener parámetros de filtro y orden
    sort_order = request.GET.get('sort', '')
    marca_filter = request.GET.get('marca', '')

    # Base queryset
    productos = Producto.objects.all()

    # Filtrar por marca
    if marca_filter:
        productos = productos.filter(marca=marca_filter)

    # Ordenar por precio
    if sort_order == 'asc':
        productos = productos.order_by('precio')
    elif sort_order == 'desc':
        productos = productos.order_by('-precio')
    else:
        productos = productos.order_by('id')  # Orden predeterminado

    # Paginación
    paginator = Paginator(productos, 10)
    page = request.GET.get('page')
    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    # Preparar los datos finales para la plantilla
    marcas = Producto.objects.values_list('marca', flat=True).distinct()

    for producto in productos:
        producto.precio_formateado = formato_precio(producto.precio)

    return render(request, 'Transaccion/catalogo_productos.html', {
        'productos': productos,
        'marcas': marcas,
        'marca_count': dict(Counter(Producto.objects.values_list('marca', flat=True))),
    })

def catalogo_servicios(request):
    """
    Muestra un catálogo de servicios permitiendo ordenar por precio.
    """
    # Obtener parámetros de filtro y orden
    sort_order = request.GET.get('sort', '')

    # Base queryset
    servicios = Servicio.objects.all()

    # Ordenar por precio
    if sort_order == 'asc':
        servicios = servicios.order_by('precio')
    elif sort_order == 'desc':
        servicios = servicios.order_by('-precio')

    # Paginación
    paginator = Paginator(servicios, 10)
    page = request.GET.get('page')
    try:
        servicios = paginator.page(page)
    except PageNotAnInteger:
        servicios = paginator.page(1)
    except EmptyPage:
        servicios = paginator.page(paginator.num_pages)

    # Formateo de precios
    for servicio in servicios:
        servicio.precio_formateado = formato_precio(servicio.precio)

    return render(request, 'Transaccion/catalogo_servicios.html', {
        'servicios': servicios,
    })

@login_required
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

@login_required
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
def agregar_venta_manual(request):
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
                return render(request, 'Transaccion/agregar_venta_manual.html', {
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
                return render(request, 'Transaccion/agregar_venta_manual.html', {
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
                return render(request, 'Transaccion/agregar_venta_manual.html', {
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
    return render(request, 'Transaccion/agregar_venta_manual.html', context)

@login_required
def gestionar_transacciones(request):
    """
    Vista para que los administradores gestionen todas las transacciones.
    """
    return render(request, 'Transaccion/gestionar_transacciones.html')

