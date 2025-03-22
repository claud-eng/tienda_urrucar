from decimal import Decimal, InvalidOperation
from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

# Configuración del logger
logger = logging.getLogger('productos')

@user_passes_test(es_administrador, login_url='home')
def listar_productos(request):
    """
    Lista todos los productos en la base de datos con opciones de filtrado,
    ordenamiento y paginación. Permite buscar por nombre, categoría, marca
    y stock.
    """
    # Recuperar todos los productos y construir el filtro
    productos = Producto.objects.all().order_by('-id') # Ordena por ID para evitar el warning de paginación
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

    # Establecer un orden por defecto si no hay criterios de ordenación
    if not sort_orders:
        sort_orders.append('-id')

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

        ''' Depuración de valores clave
        print(f"\n--- DEBUG: Producto {producto.id} ---")
        print(f"Nombre: {producto.nombre}")
        print(f"Stock Propio (consignado): {producto.consignado}")
        print(f"Precio Venta: {producto.precio}")
        print(f"Valor de Compra: {producto.precio_costo}")
        print(f"Costo Extra: {producto.costo_extra}")
        print(f"Porcentaje Consignación: {producto.porcentaje_consignacion}") '''

        # Calcular ganancia correcta
        if not producto.consignado:  # Si NO es stock propio (consignado), usa la fórmula de consignación
            if producto.porcentaje_consignacion is not None:
                ganancia = round(float(producto.precio) * (float(producto.porcentaje_consignacion) / 100), 2)
                # print(f"Ganancia Calculada (Consignación): {ganancia}")  # Depuración
                producto.ganancia_formateada = formato_precio(ganancia)
            else:
                # print("Producto consignado pero sin porcentaje definido.")
                producto.ganancia_formateada = ""
        else:  # Si es stock propio, usa el cálculo normal
            if producto.precio_costo is not None and producto.costo_extra is not None:
                ganancia = producto.precio - (producto.precio_costo + producto.costo_extra)
                # print(f"Ganancia Calculada (Stock Propio): {ganancia}")  # Depuración
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

            # Procesar imágenes adicionales con validación de tamaño
            imagenes_adicionales = []
            for imagen in request.FILES.getlist('imagenes'):
                # Validar el tamaño de cada imagen adicional
                if imagen.size > 3 * 1024 * 1024:  # 3 MB
                    messages.error(request, f"La imagen {imagen.name} supera los 3 MB y no se ha agregado.")
                    continue  # No guardar imágenes que sean demasiado grandes

                img_obj = ImagenProducto.objects.create(producto=producto, imagen=imagen)
                imagenes_adicionales.append(img_obj.imagen.url)

            # Registrar en el log la acción del usuario
            usuario = request.user
            logger.info(f"Nuevo producto agregado por: {usuario.first_name} {usuario.last_name} ({usuario.email})")
            logger.info(
                f"Detalles:\n"
                f"ID={producto.id}, Nombre={producto.nombre}, Marca={producto.marca}, Modelo={producto.modelo}, "
                f"Versión={producto.version}, Año={producto.anio}, Categoría={producto.categoria}, "
                f"Descripción={producto.descripcion}, Valor de Reserva={producto.precio_reserva}, Valor de Venta={producto.precio}, "
                f"Valor de Compra={producto.precio_costo}, Costo Extra={producto.costo_extra}, "
                f"Fecha Adquisición={producto.fecha_adquisicion.strftime('%d-%m-%Y') if producto.fecha_adquisicion else 'No especificada'}, "
                f"Stock Propio={'Sí' if producto.consignado else 'No'}, "
                f"Porcentaje Consignación={producto.porcentaje_consignacion}, "
                f"Imagen Principal={producto.imagen.url if producto.imagen else 'No tiene'}, "
                f"Imágenes Adicionales={', '.join(imagenes_adicionales) if imagenes_adicionales else 'No tiene'}"
            )

            messages.success(request, 'Producto y galería de imágenes agregados con éxito.')
            return redirect('listar_productos')
        else:
            # Si el formulario no es válido, mostrar un mensaje de error con los detalles
            error_messages = []
            datos_digitados = {}  # Almacenar lo que digitó el usuario
            errores_detallados = []  # Almacenar errores específicos

            for field, errors in form.errors.items():
                # Capturar el valor ingresado por el usuario si está en `cleaned_data`
                datos_digitados[field] = request.POST.get(field, "No ingresado")
                for error in errors:
                    error_messages.append(f"{form.fields[field].label}: {error}")
                    errores_detallados.append(f"Campo: {field} -> {error}")

            # Registrar en los logs los datos ingresados y los errores específicos
            usuario = request.user
            logger.error(
                f"Error al agregar producto por usuario: {usuario.first_name} {usuario.last_name} ({usuario.email})\n"
                f"Datos ingresados por el usuario:\n{datos_digitados}\n"
                f"Errores detectados:\n{errores_detallados}"
            )

            messages.error(request, "Hubo un error al agregar el producto: " + ", ".join(error_messages))

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
    usuario = request.user  # Obtener el usuario que edita el producto

    print(f"\n--- CARGANDO FORMULARIO ---")
    print(f"Producto encontrado: {producto.nombre} (ID: {producto.id})")
    print(f"Stock Propio en BD: {producto.consignado}")
    print(f"Porcentaje Consignación en BD: {producto.porcentaje_consignacion}")

    # Guardar los valores originales antes de la edición
    valores_anteriores = {
        'nombre': producto.nombre,
        'marca': producto.marca,
        'modelo': producto.modelo,
        'version': producto.version,
        'anio': producto.anio,
        'categoria': producto.categoria,
        'descripcion': producto.descripcion,
        'precio_reserva': producto.precio_reserva,
        'precio': producto.precio,
        'precio_costo': producto.precio_costo,
        'costo_extra': producto.costo_extra,
        'fecha_adquisicion': producto.fecha_adquisicion.strftime('%d-%m-%Y') if producto.fecha_adquisicion else 'No especificada',
        'cantidad_stock': producto.cantidad_stock,
        'consignado': 'Sí' if producto.consignado else 'No',
        'porcentaje_consignacion': producto.porcentaje_consignacion,
        'imagen': producto.imagen.url if producto.imagen else 'No tiene',
        'imagenes_adicionales': [img.imagen.url for img in imagenes_adicionales] if imagenes_adicionales else ['No tiene']
    }

    if request.method == "POST":
        print("\n--- RECIBIENDO POST ---")
        print(f"Datos enviados: {request.POST}")
        print(f"Archivos enviados: {request.FILES}")

        post_data = request.POST.copy()

        # Normalizar porcentaje consignación si está presente
        if "porcentaje_consignacion" in post_data:
            porcentaje = post_data["porcentaje_consignacion"].replace(",", ".")  # Cambiar , por .
            try:
                porcentaje = Decimal(porcentaje).normalize()
                post_data["porcentaje_consignacion"] = str(porcentaje)  # Guardar sin ceros extra
            except InvalidOperation:
                post_data["porcentaje_consignacion"] = ""  # Si hay error, dejar vacío

        form = ProductoForm(post_data, request.FILES, instance=producto)

        if form.is_valid():
            producto = form.save()

            print("\n--- DATOS POST-SAVE ---")
            print(f"Stock Propio después de guardar: {producto.consignado}")
            print(f"Porcentaje Consignación después de guardar: {producto.porcentaje_consignacion}")

            # Si `consignado` es False y el porcentaje no fue ingresado, limpiar el campo
            if not producto.consignado and not producto.porcentaje_consignacion:
                print("Producto NO consignado, eliminando porcentaje de consignación porque no fue ingresado.")
                producto.porcentaje_consignacion = None
                producto.save()

            # **Manejo de imágenes**
            imagen_principal_id = request.POST.get("imagen_principal_a_eliminar")
            if imagen_principal_id and producto.imagen:
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

            # Procesar imágenes adicionales con validación de tamaño
            for imagen in request.FILES.getlist("imagenes"):
                # Validar el tamaño de cada imagen adicional
                if imagen.size > 3 * 1024 * 1024:  # 3 MB
                    messages.error(request, f"La imagen {imagen.name} supera los 3 MB y no se ha agregado.")
                    continue  # No guardar imágenes que sean demasiado grandes

                ImagenProducto.objects.create(producto=producto, imagen=imagen)

            # Guardar valores nuevos
            valores_nuevos = {
                'nombre': producto.nombre,
                'marca': producto.marca,
                'modelo': producto.modelo,
                'version': producto.version,
                'anio': producto.anio,
                'categoria': producto.categoria,
                'descripcion': producto.descripcion,
                'precio_reserva': producto.precio_reserva,
                'precio': producto.precio,
                'precio_costo': producto.precio_costo,
                'costo_extra': producto.costo_extra,
                'fecha_adquisicion': producto.fecha_adquisicion.strftime('%d-%m-%Y') if producto.fecha_adquisicion else 'No especificada',
                'cantidad_stock': producto.cantidad_stock,
                'consignado': 'Sí' if producto.consignado else 'No',
                'porcentaje_consignacion': producto.porcentaje_consignacion,
                'imagen': producto.imagen.url if producto.imagen else 'No tiene',
                'imagenes_adicionales': [img.imagen.url for img in ImagenProducto.objects.filter(producto=producto)] if imagenes_adicionales else ['No tiene']
            }

            # Detectar cambios
            cambios = []
            for campo, valor_anterior in valores_anteriores.items():
                valor_nuevo = valores_nuevos[campo]
                if valor_anterior != valor_nuevo:
                    cambios.append(f"{campo}: {valor_anterior} -> {valor_nuevo}")

            if cambios:
                logger.info(
                    f"Producto editado por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
                    f"ID={producto.id}, Nombre={producto.nombre}\n"
                    + "\n".join(cambios)
                )

            messages.success(request, "Producto actualizado con éxito.")
            return redirect("listar_productos")

        else:
            print("\nERRORES EN EL FORMULARIO")
            print(form.errors)

            # Capturar errores del formulario y mostrarlos al usuario
            error_messages = []
            datos_digitados = {}  # Almacenar TODOS los datos ingresados, no solo los incorrectos
            errores_detallados = []  # Almacenar errores específicos

            # Capturar todos los datos ingresados por el usuario, sin traducción de nombres de campos
            for field in form.fields:
                valor_ingresado = post_data.get(field, "No ingresado")

                # Si el campo es la fecha de adquisición, convertir a formato "dd-mm-yyyy"
                if field == "fecha_adquisicion" and valor_ingresado not in ["", "No ingresado"]:
                    try:
                        fecha_obj = datetime.strptime(valor_ingresado, "%Y-%m-%d")  # Convertir de "yyyy-mm-dd"
                        valor_ingresado = fecha_obj.strftime("%d-%m-%Y")  # Formatear a "dd-mm-yyyy"
                    except ValueError:
                        valor_ingresado = "Formato incorrecto"

                datos_digitados[field] = valor_ingresado  # Guardar sin traducción

            # Capturar específicamente los errores sin traducción de nombres de campos
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{form.fields[field].label}: {error}")
                    errores_detallados.append(f"{field} -> {error}")

            # Registrar en los logs TODOS los datos ingresados sin traducción
            logger.error(
                f"Error al editar producto (ID: {producto.id}, Nombre: {producto.nombre}) por usuario: {usuario.first_name} {usuario.last_name} ({usuario.email})\n"
                f"Todos los datos ingresados:\n{datos_digitados}\n"
                f"Errores detectados:\n{errores_detallados}"
            )

            messages.error(request, "Hubo un error al actualizar el producto: " + ", ".join(error_messages))

    else:
        # Eliminar ceros innecesarios al mostrar en el formulario
        if producto.porcentaje_consignacion is not None:
            porcentaje_formateado = producto.porcentaje_consignacion.normalize()  # Elimina ceros finales
            porcentaje_formateado = str(porcentaje_formateado)  # Convertir a string
        else:
            porcentaje_formateado = ""

        form = ProductoForm(instance=producto, initial={'porcentaje_consignacion': porcentaje_formateado})
        print(f"Inicializando formulario con porcentaje consignación: {porcentaje_formateado}")

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
    usuario = request.user  # Obtener el usuario que elimina el producto

    try:
        producto = Producto.objects.get(id=producto_id)
        producto_nombre = producto.nombre  # Guardar el nombre antes de eliminarlo

        # Eliminar imagen principal si existe
        if producto.imagen and os.path.exists(producto.imagen.path):
            os.remove(producto.imagen.path)

        # Eliminar imágenes adicionales
        for imagen in producto.imagenes.all():
            if os.path.exists(imagen.imagen.path):
                os.remove(imagen.imagen.path)
            imagen.delete()  # Eliminar referencia en la base de datos

        producto.delete()  # Eliminar el producto

        # **Registrar en el log la acción del usuario**
        logger.info(
            f"Producto eliminado por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
            f"ID={producto_id}, Nombre={producto_nombre}"
        )

        messages.success(request, "Producto eliminado con éxito.")

    except Producto.DoesNotExist:
        messages.error(request, "El producto no existe.")
        logger.warning(
            f"Intento de eliminación de producto fallido por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
            f"ID={producto_id} no existe."
        )

    return redirect("listar_productos")

def catalogo_productos(request):
    """
    Muestra un catálogo de productos permitiendo filtrar por marca, ordenar por precio y disponibilidad.
    """
    # Obtener parámetros de filtro y orden
    sort_order = request.GET.get('sort', '')
    marca_filter = request.GET.get('marca', '')
    disponibilidad_filter = request.GET.get('disponibilidad', '')
    # Base queryset
    productos = Producto.objects.all()

    # Filtrar por marca
    if marca_filter:
        productos = productos.filter(marca=marca_filter)

    # Filtrar por disponibilidad
    if disponibilidad_filter == 'disponible':
        productos = productos.filter(cantidad_stock__gt=0)
    elif disponibilidad_filter == 'vendido':
        productos = productos.filter(cantidad_stock=0)

    # Ordenar por precio
    if sort_order == 'asc':
        productos = productos.order_by('precio')
    elif sort_order == 'desc':
        productos = productos.order_by('-precio')
    else:
        productos = productos.order_by('-id')  # Orden predeterminado

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
