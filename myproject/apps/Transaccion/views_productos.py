from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.

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
    productos = Producto.objects.all().order_by('nombre', 'id') # Ordena por ID para evitar el warning de paginación
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

        # Depuración de valores clave
        print(f"\n--- DEBUG: Producto {producto.id} ---")
        print(f"Nombre: {producto.nombre}")
        print(f"Stock Propio (consignado): {producto.consignado}")
        print(f"Precio Venta: {producto.precio}")
        print(f"Valor de Compra: {producto.precio_costo}")
        print(f"Costo Extra: {producto.costo_extra}")
        print(f"Porcentaje Consignación: {producto.porcentaje_consignacion}")

        # Calcular ganancia correcta
        if not producto.consignado:  # Si NO es stock propio (consignado), usa la fórmula de consignación
            if producto.porcentaje_consignacion is not None:
                ganancia = round(float(producto.precio) * (float(producto.porcentaje_consignacion) / 100), 2)
                print(f"Ganancia Calculada (Consignación): {ganancia}")  # Depuración
                producto.ganancia_formateada = formato_precio(ganancia)
            else:
                print("Producto consignado pero sin porcentaje definido.")
                producto.ganancia_formateada = ""
        else:  # Si es stock propio, usa el cálculo normal
            if producto.precio_costo is not None and producto.costo_extra is not None:
                ganancia = producto.precio - (producto.precio_costo + producto.costo_extra)
                print(f"Ganancia Calculada (Stock Propio): {ganancia}")  # Depuración
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

    print(f"\n--- CARGANDO FORMULARIO ---")
    print(f"Producto encontrado: {producto.nombre} (ID: {producto.id})")
    print(f"Stock Propio en BD: {producto.consignado}")
    print(f"Porcentaje Consignación en BD: {producto.porcentaje_consignacion}")

    if request.method == "POST":
        print("\n--- RECIBIENDO POST ---")
        print(f"Datos enviados: {request.POST}")
        print(f"Archivos enviados: {request.FILES}")

        form = ProductoForm(request.POST, request.FILES, instance=producto)

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

            for imagen in request.FILES.getlist("imagenes"):
                ImagenProducto.objects.create(producto=producto, imagen=imagen)

            messages.success(request, "Producto actualizado con éxito.")
            return redirect("listar_productos")
        else:
            print("\nERRORES EN EL FORMULARIO")
            print(form.errors)

    else:
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