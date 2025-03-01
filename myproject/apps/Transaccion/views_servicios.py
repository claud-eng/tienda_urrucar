from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

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