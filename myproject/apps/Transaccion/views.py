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
from django.contrib.auth.decorators import login_required, user_passes_test  # Importa 'login_required' y 'user_passes_test' para proteger vistas que requieren autenticación y permisos.
from django.contrib.contenttypes.models import ContentType  # Importa 'ContentType' para manejar contenido genérico en Django.
from django.core.mail import EmailMessage  # Importa 'EmailMessage' para enviar correos electrónicos.
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage  # Importa 'Paginator' y excepciones para manejar la paginación.
from django.db import transaction  # Importa 'transaction' para manejar transacciones de base de datos.
from django.db.models import Q, Count  # Importa 'Q' y 'Count' para construir consultas complejas.
from django.utils.timezone import now # Importa la función now para obtener la hora actual.
from email.headerregistry import ContentTypeHeader  # Importa 'ContentTypeHeader' para manipular encabezados de correo electrónico.
from .context_processors import formato_precio  # Importa 'formato_precio' para formatear precios en contextos de plantilla.
from .forms import * # Importa todas las funciones definidas en 'forms' del directorio actual.
from .functions import *  # Importa todas las funciones definidas en 'functions' del directorio actual.
from .models import * # Importa la función ImagenProducto para gestionar la lógica de imágenes adicionales en la galería de productos.
from django.utils import timezone  # Importa 'timezone' para manejar operaciones relacionadas con zonas horarias en Django.

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

@user_passes_test(es_administrador, login_url='home')
def listar_productos(request):
    """
    Lista todos los productos en la base de datos con opciones de filtrado,
    ordenamiento y paginación. Permite buscar por nombre, categoría, marca
    y stock.
    """
    # Recuperar todos los productos y construir el filtro
    productos = Producto.objects.all().order_by('id')  # Ordena por ID para evitar el warning de paginación
    nombre_query = request.GET.get('nombre')
    stock_query = request.GET.get('stock')
    categoria_filter = request.GET.get('categoria')
    marca_query = request.GET.get('marca')
    sort_order = request.GET.get('sort')

    # Construir el filtro dinámico
    query = Q()
    if nombre_query:
        query &= Q(nombre__icontains=nombre_query)
    if categoria_filter:
        query &= Q(categoria=categoria_filter)
    if marca_query:
        query &= Q(marca__icontains=marca_query)

    # Ordenar según los criterios especificados
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

    # Configurar la paginación
    paginator = Paginator(productos, 5)
    page = request.GET.get('page')

    try:
        productos = paginator.page(page)
    except PageNotAnInteger:
        productos = paginator.page(1)
    except EmptyPage:
        productos = paginator.page(paginator.num_pages)

    # Formatear y calcular los datos de cada producto
    for producto in productos:
        producto.precio_formateado = formato_precio(producto.precio)
        producto.precio_reserva_formateado = (
            formato_precio(producto.precio_reserva) if producto.precio_reserva else None
        )
        producto.precio_costo_formateado = (
            formato_precio(producto.precio_costo) if producto.precio_costo else None
        )
        producto.costo_extra_formateado = (
            formato_precio(producto.costo_extra) if producto.costo_extra else None
        )

        # Calcular ganancia basada en si el producto es consignado o no
        if producto.consignado:
            if producto.porcentaje_consignacion is not None:
                ganancia = round(producto.precio * (producto.porcentaje_consignacion / 100), 2)
                producto.ganancia_formateada = formato_precio(ganancia)
            else:
                producto.ganancia_formateada = ""  # Si no tiene porcentaje, no hay ganancia
        else:
            if producto.precio_costo is not None and producto.costo_extra is not None:
                ganancia = producto.precio - (producto.precio_costo + producto.costo_extra)
                producto.ganancia_formateada = formato_precio(ganancia)
            else:
                producto.ganancia_formateada = ""

    # Indicar si hay una consulta de búsqueda activa
    has_search_query_nombre = bool(nombre_query)

    return render(request, 'Transaccion/listar_productos.html', {
        'productos': productos,
        'has_search_query_nombre': has_search_query_nombre,
    })

@user_passes_test(es_administrador, login_url='home')
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

@user_passes_test(es_administrador, login_url='home')
def editar_producto(request, producto_id):
    """
    Permite editar un producto existente, asegurando que el porcentaje de consignación
    se cargue correctamente y que las imágenes adicionales se gestionen bien.
    """
    producto = get_object_or_404(Producto, id=producto_id)
    imagenes_adicionales = ImagenProducto.objects.filter(producto=producto)  # Obtener imágenes adicionales

    print(f"Producto encontrado: {producto.nombre} (ID: {producto.id})")
    print(f"Consignado en DB: {producto.consignado}")
    print(f"Porcentaje Consignación en DB: {producto.porcentaje_consignacion}")

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        
        if form.is_valid():
            producto = form.save()

            # Si `consignado` es "No", limpiar el campo `porcentaje_consignacion`
            if not producto.consignado:
                print("Producto NO consignado, eliminando porcentaje de consignación.")
                producto.porcentaje_consignacion = None
                producto.save()

            # **Manejo de imágenes**
            # Eliminar imagen principal si está marcada para eliminación
            imagen_principal_id = request.POST.get("imagen_principal_a_eliminar")
            if imagen_principal_id and producto.imagen:
                if os.path.exists(producto.imagen.path):
                    os.remove(producto.imagen.path)  # Elimina físicamente el archivo
                producto.imagen.delete(save=False)
                producto.imagen = None
                producto.save()

            # Eliminar imágenes adicionales seleccionadas
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
            print("Errores en el formulario:")
            print(form.errors)
            messages.error(request, "Hubo errores en el formulario, revisa los campos.")
    
    else:
        # **Aquí verificamos que el formulario reciba el valor de porcentaje_consignacion**
        form = ProductoForm(instance=producto, initial={'porcentaje_consignacion': producto.porcentaje_consignacion})
        print(f"Inicializando formulario con porcentaje consignación: {form.initial.get('porcentaje_consignacion')}")

    return render(request, "Transaccion/editar_producto.html", {
        "form": form,
        "producto": producto,
        "imagenes_adicionales": imagenes_adicionales,  # Pasa las imágenes adicionales al contexto
    })

@user_passes_test(es_administrador, login_url='home')
# Eliminar imagen adicional
def eliminar_imagen_adicional(request, imagen_id):
    imagen = get_object_or_404(ImagenProducto, id=imagen_id)
    if os.path.exists(imagen.imagen.path):
        os.remove(imagen.imagen.path)  # Elimina el archivo físicamente
    imagen.delete()  # Elimina la referencia de la base de datos
    messages.success(request, 'La imagen adicional fue eliminada con éxito.')
    return redirect('editar_producto', producto_id=imagen.producto.id)

@user_passes_test(es_administrador, login_url='home')
def confirmar_borrar_producto(request, producto_id):
    """
    Confirma la eliminación de un producto mostrando una página de confirmación.
    """
    producto = Producto.objects.get(id=producto_id)
    return render(request, 'Transaccion/confirmar_borrar_producto.html', {'producto': producto})

@user_passes_test(es_administrador, login_url='home')
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

@user_passes_test(es_administrador, login_url='home')
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

@user_passes_test(es_administrador, login_url='home')
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

@user_passes_test(es_administrador, login_url='home')
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

@user_passes_test(es_administrador, login_url='home')
def confirmar_borrar_servicio(request, servicio_id):
    """
    Muestra una página de confirmación antes de eliminar un servicio.
    """
    servicio = Servicio.objects.get(id=servicio_id)
    return render(request, 'Transaccion/confirmar_borrar_servicio.html', {'servicio': servicio})

@user_passes_test(es_administrador, login_url='home')
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

def formulario_servicios(request, id):
    """
    Renderiza un formulario para solicitar servicios y envía un correo al administrador con los datos capturados.
    """
    servicio = get_object_or_404(Servicio, id=id)

    # Define las preguntas específicas por servicio
    preguntas_por_servicio = {
        'Desabolladura & pintura': [
            {'nombre': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True},
            {'nombre': 'apellido', 'etiqueta': 'Apellido', 'obligatorio': True},
            {'nombre': 'rut', 'etiqueta': 'RUT', 'obligatorio': True},
            {'nombre': 'correo', 'etiqueta': 'Correo', 'obligatorio': True, 'tipo': 'email'},
            {'nombre': 'telefono', 'etiqueta': 'Teléfono', 'obligatorio': True},
            {'nombre': 'patente', 'etiqueta': 'Patente', 'obligatorio': True},
            {'nombre': 'marca', 'etiqueta': 'Marca', 'obligatorio': True},
            {'nombre': 'modelo', 'etiqueta': 'Modelo', 'obligatorio': True},
            {'nombre': 'direccion', 'etiqueta': 'Dirección', 'obligatorio': True},
            {'nombre': 'comuna', 'etiqueta': 'Comuna', 'obligatorio': True},
            {'nombre': 'fotos', 'etiqueta': 'Fotos (Opcional)', 'obligatorio': False, 'tipo': 'file', 'maximo': 5},
            {'nombre': 'observaciones', 'etiqueta': 'Observaciones (Opcional)', 'obligatorio': False},
        ],
        'Consignación virtual': [
            {'nombre': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True},
            {'nombre': 'apellido', 'etiqueta': 'Apellido', 'obligatorio': True},
            {'nombre': 'rut', 'etiqueta': 'RUT', 'obligatorio': True},
            {'nombre': 'correo', 'etiqueta': 'Correo', 'obligatorio': True, 'tipo': 'email'},
            {'nombre': 'telefono', 'etiqueta': 'Teléfono', 'obligatorio': True},
            {'nombre': 'patente', 'etiqueta': 'Patente', 'obligatorio': True},
            {'nombre': 'marca', 'etiqueta': 'Marca', 'obligatorio': True},
            {'nombre': 'modelo', 'etiqueta': 'Modelo', 'obligatorio': True},
            {'nombre': 'anio', 'etiqueta': 'Año', 'obligatorio': True, 'tipo': 'number'},
            {'nombre': 'kilometraje', 'etiqueta': 'Kilometraje', 'obligatorio': True, 'tipo': 'number'},
            {'nombre': 'n_propietarios', 'etiqueta': 'N° de Propietarios', 'obligatorio': False, 'tipo': 'number'},
            {'nombre': 'n_llaves', 'etiqueta': 'N° Copias de Llave', 'obligatorio': False, 'tipo': 'number'},
            {'nombre': 'direccion', 'etiqueta': 'Dirección', 'obligatorio': True},
            {'nombre': 'comuna', 'etiqueta': 'Comuna', 'obligatorio': True},
            {'nombre': 'fotos_exterior', 'etiqueta': 'Adjuntar Fotos Exterior', 'obligatorio': True, 'tipo': 'file', 'minimo': 4, 'maximo': 6},
            {'nombre': 'fotos_interior', 'etiqueta': 'Adjuntar Fotos Interior', 'obligatorio': True, 'tipo': 'file', 'minimo': 3, 'maximo': 6},
            {'nombre': 'observaciones', 'etiqueta': 'Observaciones ', 'obligatorio': True},
        ],
        'Mecánico automotriz': [
            {'nombre': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True},
            {'nombre': 'apellido', 'etiqueta': 'Apellido', 'obligatorio': True},
            {'nombre': 'rut', 'etiqueta': 'RUT', 'obligatorio': True},
            {'nombre': 'correo', 'etiqueta': 'Correo', 'obligatorio': True, 'tipo': 'email'},
            {'nombre': 'telefono', 'etiqueta': 'Teléfono', 'obligatorio': True},
            {'nombre': 'patente', 'etiqueta': 'Patente', 'obligatorio': True},
            {'nombre': 'marca', 'etiqueta': 'Marca', 'obligatorio': True},
            {'nombre': 'modelo', 'etiqueta': 'Modelo', 'obligatorio': True},
            {'nombre': 'direccion', 'etiqueta': 'Dirección', 'obligatorio': True},
            {'nombre': 'comuna', 'etiqueta': 'Comuna', 'obligatorio': True},
            {'nombre': 'fotos', 'etiqueta': 'Fotos (Opcional)', 'obligatorio': False, 'tipo': 'file', 'maximo': 5},
            {'nombre': 'observaciones', 'etiqueta': 'Observaciones (Opcional)', 'obligatorio': False},
        ],
        'Repuestos': [
            {'nombre': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True},
            {'nombre': 'apellido', 'etiqueta': 'Apellido', 'obligatorio': True},
            {'nombre': 'rut', 'etiqueta': 'RUT', 'obligatorio': True},
            {'nombre': 'correo', 'etiqueta': 'Correo', 'obligatorio': True, 'tipo': 'email'},
            {'nombre': 'telefono', 'etiqueta': 'Teléfono', 'obligatorio': True},
            {'nombre': 'patente', 'etiqueta': 'Patente', 'obligatorio': True},
            {'nombre': 'marca', 'etiqueta': 'Marca', 'obligatorio': True},
            {'nombre': 'modelo', 'etiqueta': 'Modelo', 'obligatorio': True},
            {'nombre': 'anio', 'etiqueta': 'Año', 'obligatorio': True, 'tipo': 'number'},
            {'nombre': 'vin', 'etiqueta': 'VIN (N° Chasis)', 'obligatorio': True},
            {'nombre': 'repuesto', 'etiqueta': 'Repuesto', 'obligatorio': True},
            {'nombre': 'direccion', 'etiqueta': 'Dirección', 'obligatorio': True},
            {'nombre': 'comuna', 'etiqueta': 'Comuna', 'obligatorio': True},
            {'nombre': 'observaciones', 'etiqueta': 'Observaciones (Opcional)', 'obligatorio': False},
        ],
        'Cambio de batería': [
            {'nombre': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True},
            {'nombre': 'apellido', 'etiqueta': 'Apellido', 'obligatorio': True},
            {'nombre': 'rut', 'etiqueta': 'RUT', 'obligatorio': True},
            {'nombre': 'correo', 'etiqueta': 'Correo', 'obligatorio': True, 'tipo': 'email'},
            {'nombre': 'telefono', 'etiqueta': 'Teléfono', 'obligatorio': True},
            {'nombre': 'patente', 'etiqueta': 'Patente', 'obligatorio': True},
            {'nombre': 'marca', 'etiqueta': 'Marca', 'obligatorio': True},
            {'nombre': 'modelo', 'etiqueta': 'Modelo', 'obligatorio': True},
            {'nombre': 'anio', 'etiqueta': 'Año', 'obligatorio': True, 'tipo': 'number'},
            {'nombre': 'direccion', 'etiqueta': 'Dirección', 'obligatorio': True},
            {'nombre': 'comuna', 'etiqueta': 'Comuna', 'obligatorio': True},
            {'nombre': 'observaciones', 'etiqueta': 'Observaciones (Opcional)', 'obligatorio': False},
        ],
        'Traslado en grúa': [
            {'nombre': 'nombre', 'etiqueta': 'Nombre', 'obligatorio': True},
            {'nombre': 'apellido', 'etiqueta': 'Apellido', 'obligatorio': True},
            {'nombre': 'rut', 'etiqueta': 'RUT', 'obligatorio': True},
            {'nombre': 'correo', 'etiqueta': 'Correo', 'obligatorio': True, 'tipo': 'email'},
            {'nombre': 'telefono', 'etiqueta': 'Teléfono', 'obligatorio': True},
            {'nombre': 'patente', 'etiqueta': 'Patente', 'obligatorio': True},
            {'nombre': 'marca', 'etiqueta': 'Marca', 'obligatorio': True},
            {'nombre': 'modelo', 'etiqueta': 'Modelo', 'obligatorio': True},
            {'nombre': 'direccion_origen', 'etiqueta': 'Dirección de Origen', 'obligatorio': True},
            {'nombre': 'comuna_origen', 'etiqueta': 'Comuna de Origen', 'obligatorio': True},
            {'nombre': 'direccion_destino', 'etiqueta': 'Dirección de Destino', 'obligatorio': True},
            {'nombre': 'comuna_destino', 'etiqueta': 'Comuna de Destino', 'obligatorio': True},
            {'nombre': 'observaciones', 'etiqueta': 'Observaciones (Opcional)', 'obligatorio': False},
        ],
    }

    # Obtener las preguntas específicas del servicio
    preguntas = preguntas_por_servicio.get(servicio.nombre, [])

    # Si el usuario está autenticado, rellenar campos predeterminados
    if request.user.is_authenticated:
        cliente = Cliente.objects.filter(user=request.user).first()  # Buscar el cliente relacionado
        for pregunta in preguntas:
            pregunta['valor'] = ''  # Inicializar el valor predeterminado como vacío
            pregunta['readonly'] = False  # Por defecto, los campos no son de solo lectura
            if pregunta['nombre'] == 'nombre':
                pregunta['valor'] = request.user.first_name
                pregunta['readonly'] = True
            elif pregunta['nombre'] == 'apellido':
                pregunta['valor'] = request.user.last_name
                pregunta['readonly'] = True
            elif pregunta['nombre'] == 'correo':
                pregunta['valor'] = request.user.email
                pregunta['readonly'] = True
            elif pregunta['nombre'] == 'telefono':
                # Verificar si el cliente tiene un número de teléfono
                pregunta['valor'] = cliente.numero_telefono if cliente else ''
                pregunta['readonly'] = True

    # Procesar las preguntas para evitar errores en la plantilla
    for pregunta in preguntas:
        pregunta['minimo'] = pregunta.get('minimo', None)
        pregunta['maximo'] = pregunta.get('maximo', None)

    success = None  # Variable para indicar éxito
    error = None  # Variable para indicar errores específicos

    if request.method == 'POST':
        # Capturar los datos enviados por el formulario
        datos_formulario = {pregunta['nombre']: request.POST.get(pregunta['nombre']) for pregunta in preguntas}
        archivos = {pregunta['nombre']: request.FILES.getlist(pregunta['nombre']) for pregunta in preguntas if pregunta.get('tipo') == 'file'}

        # Validar campos obligatorios
        for pregunta in preguntas:
            if pregunta['obligatorio']:
                if pregunta.get('tipo') == 'file':
                    cantidad_imagenes = len(archivos.get(pregunta['nombre'], []))
                    if cantidad_imagenes < pregunta.get('minimo', 0):
                        error = f"El campo {pregunta['etiqueta']} requiere un mínimo de {pregunta['minimo']} imágenes."
                        break
                elif not datos_formulario.get(pregunta['nombre']):
                    error = f"El campo {pregunta['etiqueta']} es obligatorio."
                    break

        # Validar cantidad máxima de imágenes
        if not error:
            for pregunta in preguntas:
                if pregunta.get('tipo') == 'file' and pregunta.get('maximo'):
                    cantidad_imagenes = len(archivos.get(pregunta['nombre'], []))
                    if cantidad_imagenes > pregunta['maximo']:
                        error = f"El campo {pregunta['etiqueta']} permite un máximo de {pregunta['maximo']} imágenes."
                        break

        # Enviar el correo si no hay errores
        if not error:
            try:
                asunto = "Has recibido una solicitud por un servicio"
                mensaje = f"Se ha recibido una solicitud para el servicio: {servicio.nombre}\n\n"

                # Datos del comprador
                mensaje += "Datos del comprador:\n"
                for pregunta in preguntas:
                    if pregunta['nombre'] in ['nombre', 'apellido', 'rut', 'correo', 'telefono']:
                        mensaje += f"{pregunta['etiqueta']}: {datos_formulario.get(pregunta['nombre'], 'N/A')}\n"
                mensaje += "\n"

                # Información del servicio
                mensaje += "\nInformación del servicio:\n"
                for pregunta in preguntas:
                    if pregunta['nombre'] not in ['nombre', 'apellido', 'rut', 'correo', 'telefono'] and pregunta.get('tipo') != 'file':
                        mensaje += f"{pregunta['etiqueta']}: {datos_formulario.get(pregunta['nombre'], 'N/A')}\n"

                # Configurar el correo
                email = EmailMessage(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, ["automotriz@urrucar.cl"])
                for nombre_campo, archivos_campo in archivos.items():
                    for archivo in archivos_campo:
                        email.attach(archivo.name, archivo.read(), archivo.content_type)

                email.send(fail_silently=False)
                success = True
            except Exception as e:
                error = f"Error al enviar la solicitud: {e}"

    # Renderizar la plantilla con mensajes de éxito o error
    if not success and error:
        messages.error(request, error)

    return render(request, 'Transaccion/formulario_servicios.html', {
        'servicio': servicio,
        'preguntas': preguntas,
        'success': success,
    })

@user_passes_test(es_administrador, login_url='home')
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

    # Si el usuario es cliente, solo ve sus ventas
    if hasattr(request.user, 'cliente'):
        query &= Q(cliente=request.user.cliente)

    # Si es administrador, puede filtrar por nombre y apellido
    elif hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador':
        if cliente_query:
            palabras = cliente_query.split()
            for palabra in palabras:
                query &= (
                    Q(cliente__user__first_name__icontains=palabra) | 
                    Q(cliente__user__last_name__icontains=palabra) | 
                    Q(cliente_anonimo__nombre__icontains=palabra) | 
                    Q(cliente_anonimo__apellido__icontains=palabra)
                )
    else:
        return redirect('home')
    
    ordenes_compra = VentaOnline.objects.filter(query).order_by('-fecha')

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
        ganancia_total = 0

        for detalle in orden.detalleventaonline_set.all():
            ganancia_detalle = 0  # Default: 0

            # Verificar si es un producto
            if detalle.producto:
                if detalle.producto.categoria == "Vehículo":
                    # Vehículo: Ganancia depende del estado
                    if detalle.estado_reserva == "Vendida":
                        ganancia_detalle = detalle.producto.ganancia * detalle.cantidad
                    else:
                        # En proceso o Desistida: ganancia es 0
                        ganancia_detalle = 0
                else:
                    # No es vehículo: Usar el total pagado como ganancia
                    ganancia_detalle = detalle.precio * detalle.cantidad
            else:
                # Servicios: Usar el total pagado como ganancia
                ganancia_detalle = detalle.precio * detalle.cantidad

            ganancia_total += ganancia_detalle

            detalles_formateados.append({
                'nombre': detalle.producto.nombre if detalle.producto else detalle.servicio.nombre,
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(detalle.precio),
                'ganancia_formateada': formato_precio(ganancia_detalle),
                'es_producto': bool(detalle.producto),
            })

        orden.detalles_formateados = detalles_formateados
        orden.ganancia_formateada = formato_precio(ganancia_total)

    context = {
        'ordenes_paginadas': ordenes_paginadas,
        'cliente_query': cliente_query,
        'es_administrador': hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador'
    }

    return render(request, 'Transaccion/listar_ventas_online.html', context)

@user_passes_test(es_administrador, login_url='home')
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
                    # Si el estado cambia a 'Vendida' o 'Desistida', actualizar campos adicionales
                    if nuevo_estado in ['Vendida', 'Desistida']:
                        if not detalle.fecha_estado_final:
                            detalle.fecha_estado_final = now()
                            # Calcular días transcurridos desde la transacción
                            diferencia = detalle.fecha_estado_final - venta.fecha
                            detalle.calculo_tiempo_transcurrido = max(diferencia.days, 0)  # Asignar 0 si es el mismo día
                    else:
                        # Limpiar los campos si el estado no es final
                        detalle.fecha_estado_final = None
                        detalle.calculo_tiempo_transcurrido = None
                    detalle.save()
        messages.success(request, "Estado de la reserva actualizado correctamente.")
        return redirect("listar_ventas_online")

    # Preparar detalles para el formulario
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

@user_passes_test(es_administrador, login_url='home')
def listar_ventas_manuales(request):
    """
    Lista todas las ventas registradas de forma manual, con opciones de búsqueda por cliente anónimo
    y paginación. Muestra los detalles de productos y servicios para cada venta.
    """
    cliente_query = request.GET.get('cliente', '')
    query = Q()

    # Filtrar si el usuario es administrador
    if hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador':
        if cliente_query:
            # Dividir la búsqueda en palabras (nombre y apellido/s)
            palabras = cliente_query.split()
            
            for palabra in palabras:
                # Se agrega un filtro por cada palabra, pero todos deben coincidir (AND)
                query &= (
                    Q(cliente_anonimo__nombre__icontains=palabra) |
                    Q(cliente_anonimo__apellido__icontains=palabra)
                )
    else:
        return redirect('home')

    ventas_filtradas = VentaManual.objects.filter(query).order_by('-fecha_creacion')

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

        # Formatear precios usando formato_precio
        venta.total_formateado = formato_precio(venta.total)
        venta.pago_cliente_formateado = formato_precio(venta.pago_cliente)
        venta.cambio_formateado = formato_precio(venta.cambio)

        # Calcular ganancia o pérdida basada en pago_cliente
        total_costo = sum(detalle.precio_costo or 0 for detalle in productos) + \
                    sum(detalle.precio_costo or 0 for detalle in servicios)
        ganancia_perdida = venta.pago_cliente - total_costo

        productos_formateados = []
        for detalle in productos:
            productos_formateados.append({
                'nombre': detalle.producto.nombre,
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(detalle.producto.precio),
                'precio_costo': formato_precio(detalle.precio_costo),  # Agregamos precio_costo
            })

        servicios_formateados = []
        for detalle in servicios:
            precio = (
                formato_precio(detalle.servicio.precio)
                if detalle.servicio.precio > 0
                else formato_precio(venta.precio_personalizado or 0)
            )
            servicios_formateados.append({
                'nombre': detalle.servicio.nombre,
                'precio_formateado': precio,
                'precio_costo': formato_precio(detalle.precio_costo),  # Agregamos precio_costo
            })

        ventas_list.append({
            'venta': venta,
            'productos': productos_formateados,
            'servicios': servicios_formateados,
            'tiene_productos': productos.exists(),
            'tiene_servicios': servicios.exists(),
            'ganancia_perdida': formato_precio(ganancia_perdida),
        })

    return render(request, 'Transaccion/listar_ventas_manuales.html', {
        'ventas_list': ventas_list,
        'ventas_paginadas': ventas_paginadas,
        'cliente_query': cliente_query,
    })

@user_passes_test(es_administrador, login_url='home')
def agregar_venta_manual(request):
    """
    Permite agregar una nueva venta manual de servicios asociada a un cliente anónimo.
    """
    orden_compra_form = VentaManualForm(request.POST or None)
    detalle_servicio_form = DetalleVentaManualServicioForm(request.POST or None)
    cliente_anonimo_form = ClienteAnonimoForm(request.POST or None)

    if request.method == 'POST':
        if (
            orden_compra_form.is_valid()
            and detalle_servicio_form.is_valid()
            and cliente_anonimo_form.is_valid()
        ):
            # Calcular el total manualmente
            servicio = detalle_servicio_form.cleaned_data.get('servicio')
            precio_costo = detalle_servicio_form.cleaned_data.get('precio_costo', 0)
            total_servicios = servicio.precio if servicio else 0
            precio_personalizado = orden_compra_form.cleaned_data.get('precio_personalizado', 0)
            total_venta = max(total_servicios, precio_personalizado)

            # Validar el monto del pago
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)
            if pago_cliente > total_venta:
                messages.error(request, 'El monto del pago no puede ser mayor al total.')
                return render(request, 'Transaccion/agregar_venta_manual.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_servicio_form': detalle_servicio_form,
                    'cliente_anonimo_form': cliente_anonimo_form,
                })

            # Crear cliente anónimo
            cliente_anonimo = cliente_anonimo_form.save(commit=False)
            cliente_anonimo.session_key = f"anonimo_{cliente_anonimo.nombre.lower()}{cliente_anonimo.apellido.lower()}{now().strftime('%Y%m%d%H%M%S')}"
            cliente_anonimo.save()

            # Guardar la venta
            with transaction.atomic():
                orden_compra = orden_compra_form.save(commit=False)
                orden_compra.cliente_anonimo = cliente_anonimo
                orden_compra.total = total_venta
                orden_compra.cambio = max(pago_cliente - total_venta, 0)

                # Registrar fecha de pago final si el monto pagado es igual al total
                if pago_cliente >= total_venta:
                    orden_compra.fecha_pago_final = now()
                else:
                    orden_compra.fecha_pago_final = None

                orden_compra.save()

                # Guardar el detalle del servicio
                detalle = detalle_servicio_form.save(commit=False)
                detalle.orden_compra = orden_compra
                detalle.cantidad = 1  # Siempre será 1 para servicios
                detalle.save()

            messages.success(request, 'Venta registrada exitosamente.')
            return redirect('listar_ventas_manuales')

        # Mostrar errores si alguno de los formularios no es válido
        print("Errores en orden_compra_form:", orden_compra_form.errors)
        print("Errores en detalle_servicio_form:", detalle_servicio_form.errors)
        print("Errores en cliente_anonimo_form:", cliente_anonimo_form.errors)

    # Contexto para renderizar el formulario
    context = {
        'orden_compra_form': orden_compra_form,
        'detalle_servicio_form': detalle_servicio_form,
        'cliente_anonimo_form': cliente_anonimo_form,
    }
    return render(request, 'Transaccion/agregar_venta_manual.html', context)

@user_passes_test(es_administrador, login_url='home')
def editar_venta_manual(request, venta_id):
    """
    Permite editar una venta manual existente, actualizando el precio de costo y el pago del cliente,
    manteniendo intacto el precio personalizado.
    """
    venta = get_object_or_404(VentaManual, id=venta_id)
    orden_compra_form = VentaManualForm(request.POST or None, instance=venta)
    detalle_servicio = venta.detalleventamanual_set.filter(servicio__isnull=False).first()
    detalle_servicio_form = DetalleVentaManualServicioForm(request.POST or None, instance=detalle_servicio)

    if request.method == 'POST':
        print("POST recibido:", request.POST)
        if orden_compra_form.is_valid() and detalle_servicio_form.is_valid():
            # Validar que el monto pagado por el cliente no exceda el total
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)
            total_venta = venta.total
            if pago_cliente > total_venta:
                messages.error(request, 'El monto del pago no puede ser mayor al total.')
                return render(request, 'Transaccion/editar_venta_manual.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_servicio_form': detalle_servicio_form,
                    'venta': venta,
                })

            detalle_actualizado = detalle_servicio_form.save(commit=False)
            detalle_actualizado.save()

            venta_actualizada = orden_compra_form.save(commit=False)
            print("Datos de venta antes de guardar:", venta_actualizada.__dict__)

            # Si el pago del cliente iguala o supera el total, actualizar la fecha de pago final
            if venta_actualizada.pago_cliente >= venta_actualizada.total:
                if not venta_actualizada.fecha_pago_final:
                    venta_actualizada.fecha_pago_final = timezone.now()
                    print("Fecha de pago final actualizada a:", venta_actualizada.fecha_pago_final)
            else:
                # Si el pago no es completo, limpiar la fecha de pago final
                venta_actualizada.fecha_pago_final = None
                print("Pago incompleto, fecha de pago final reseteada a None")

            venta_actualizada.save()
            print("Datos de venta después de guardar:", venta_actualizada.__dict__)

            messages.success(request, 'Venta manual actualizada correctamente.')
            return redirect('listar_ventas_manuales')
        else:
            print("Errores en los formularios:")
            print("Orden compra form:", orden_compra_form.errors)
            print("Detalle servicio form:", detalle_servicio_form.errors)
            messages.error(request, 'Errores en el formulario de edición.')

    return render(request, 'Transaccion/editar_venta_manual.html', {
        'orden_compra_form': orden_compra_form,
        'detalle_servicio_form': detalle_servicio_form,
        'venta': venta,
    })

@user_passes_test(es_administrador, login_url='home')
def gestionar_transacciones(request):
    """
    Vista para que los administradores gestionen todas las transacciones.
    """
    return render(request, 'Transaccion/gestionar_transacciones.html')

@user_passes_test(es_administrador, login_url='home')
def ver_reportes(request):
    """
    Vista para ver reportes de todas las transacciones.
    """
    return render(request, 'Transaccion/ver_reportes.html')
