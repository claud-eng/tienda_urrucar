from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

@login_required
def listar_ventas_online(request):
    """
    Lista todas las ventas aprobadas, separando productos y servicios en tablas distintas.
    Se incluyen filtros de búsqueda y paginación.
    """
    cliente_query = request.GET.get('cliente', '')

    # Filtrar solo ventas aprobadas
    query = Q(estado='aprobada')

    # Si el usuario es cliente, solo ve sus ventas
    if hasattr(request.user, 'cliente'):
        query &= Q(cliente=request.user.cliente)

    # Si es administrador, permite filtrar por cliente
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

    # Obtener ventas filtradas y ordenarlas por fecha
    ventas_filtradas = VentaOnline.objects.filter(query).order_by('-fecha')

    # Separar ventas de productos y servicios
    ventas_productos = ventas_filtradas.filter(detalleventaonline__producto__isnull=False).distinct()
    ventas_servicios = ventas_filtradas.filter(detalleventaonline__servicio__isnull=False).distinct()

    # Paginación independiente para productos y servicios
    paginator_productos = Paginator(ventas_productos, 5)
    paginator_servicios = Paginator(ventas_servicios, 5)

    page_productos = request.GET.get('page_productos')
    page_servicios = request.GET.get('page_servicios')

    try:
        ventas_productos_paginadas = paginator_productos.page(page_productos)
    except PageNotAnInteger:
        ventas_productos_paginadas = paginator_productos.page(1)
    except EmptyPage:
        ventas_productos_paginadas = paginator_productos.page(paginator_productos.num_pages)

    try:
        ventas_servicios_paginadas = paginator_servicios.page(page_servicios)
    except PageNotAnInteger:
        ventas_servicios_paginadas = paginator_servicios.page(1)
    except EmptyPage:
        ventas_servicios_paginadas = paginator_servicios.page(paginator_servicios.num_pages)

    # Generar listas con información formateada
    ventas_productos_list = []
    ventas_servicios_list = []

    for venta in ventas_productos_paginadas:
        productos = venta.detalleventaonline_set.filter(producto__isnull=False)

        # Formatear precios
        venta.total_formateado = formato_precio(venta.total)
        ganancia_total = 0
        productos_formateados = []

        for detalle in productos:
            producto = detalle.producto
            ganancia_detalle = 0

            # Mostrar datos del producto antes del cálculo
            print(f"\nDEPURACIÓN - Producto en Venta Online:")
            print(f"Orden ID: {venta.id}")
            print(f"Nombre: {producto.nombre}")
            print(f"Stock Propio: {'Sí' if producto.consignado else 'No'}")
            print(f"Precio Venta (de Producto): {producto.precio}")
            print(f"Precio Venta (desde Detalle): {detalle.precio}")  # Verificación
            print(f"Valor de Compra: {producto.precio_costo}")
            print(f"Costo Extra: {producto.costo_extra}")
            print(f"Porcentaje Consignación: {producto.porcentaje_consignacion}")
            print(f"Estado de Reserva: {detalle.estado_reserva}")
            print(f"Cantidad Vendida: {detalle.cantidad}")

            # Aplicar cálculo de ganancia solo si la reserva es "Vendida"
            if detalle.estado_reserva == "Vendida":
                if not producto.consignado:  
                    # Producto CONSIGNADO
                    if producto.porcentaje_consignacion is not None:
                        ganancia_detalle = round((producto.precio * (producto.porcentaje_consignacion / 100)) * detalle.cantidad, 2)
                        print(f"Ganancia Calculada (Consignación, corregida): {ganancia_detalle}")
                    else:
                        print("Producto consignado pero sin porcentaje definido. Ganancia = 0")
                else:  
                    # Producto PROPIO (STOCK PROPIO)
                    if producto.precio_costo is not None and producto.costo_extra is not None:
                        ganancia_detalle = max((producto.precio - producto.precio_costo - producto.costo_extra) * detalle.cantidad, 0)
                        print(f"Ganancia Calculada (Stock Propio, corregida): {ganancia_detalle}")
                    else:
                        ganancia_detalle = 0
                        print("Faltan valores de precio de costo o costo extra. Ganancia = 0")

            ganancia_total += ganancia_detalle

            productos_formateados.append({
                'nombre': producto.nombre,
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(detalle.precio),
                'ganancia_formateada': formato_precio(ganancia_detalle),
                'stock_propio': "Sí" if producto.consignado else "No",
            })

        print(f"\nTOTAL GANANCIAS PRODUCTOS EN ESTA VENTA (Orden {venta.id}): {ganancia_total}")

        ventas_productos_list.append({
            'venta': venta,
            'productos': productos_formateados,
            'ganancia_formateada': formato_precio(ganancia_total),
        })

    for venta in ventas_servicios_paginadas:
        servicios = venta.detalleventaonline_set.filter(servicio__isnull=False)

        # Formateo de precios
        venta.total_formateado = formato_precio(venta.total)
        ganancia_total = 0
        servicios_formateados = []

        for detalle in servicios:
            ganancia_detalle = detalle.precio * detalle.cantidad
            ganancia_total += ganancia_detalle

            servicios_formateados.append({
                'nombre': detalle.servicio.nombre,
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(detalle.precio),
                'ganancia_formateada': formato_precio(ganancia_detalle),
            })

        ventas_servicios_list.append({
            'venta': venta,
            'servicios': servicios_formateados,
            'ganancia_formateada': formato_precio(ganancia_total),
        })

    context = {
        'ventas_productos_list': ventas_productos_list,
        'ventas_servicios_list': ventas_servicios_list,
        'ventas_productos_paginadas': ventas_productos_paginadas,
        'ventas_servicios_paginadas': ventas_servicios_paginadas,
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

    # Configurar el logger
    logger = logging.getLogger("ventas_online")
                           
    venta = get_object_or_404(VentaOnline, id=venta_id)
    usuario = request.user  # Usuario que realiza la edición

    if request.method == "POST":
        cambios_realizados = []

        # Iterar por cada detalle de la venta
        for detalle in venta.detalleventaonline_set.all():
            if detalle.producto and detalle.producto.categoria == "Vehículo":
                estado_anterior = detalle.estado_reserva  # Guardamos el estado anterior
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

                    # Guardar los cambios en la lista de logs
                    cambios_realizados.append(
                        f"Producto: {detalle.producto.nombre}\n"
                        f"Estado: {estado_anterior} -> {nuevo_estado}"
                    )

        if cambios_realizados:
            logger.info(
                f"Edición de venta online realizada por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
                f"Venta ID: {venta.id}\n"
                f"Número de Orden: {venta.numero_orden}\n"
                + "".join(cambios_realizados)
            )

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
    cliente_query = request.GET.get('cliente', '')
    query = Q()

    if hasattr(request.user, 'empleado') and request.user.empleado.rol == 'Administrador':
        if cliente_query:
            palabras = cliente_query.split()
            for palabra in palabras:
                query &= (
                    Q(cliente_anonimo__nombre__icontains=palabra) |
                    Q(cliente_anonimo__apellido__icontains=palabra)
                )
    else:
        return redirect('home')

    ventas_filtradas = VentaManual.objects.filter(query).order_by('-fecha_creacion')

    # Separar productos y servicios
    productos_ventas = ventas_filtradas.filter(detalleventamanual_set__producto__isnull=False).distinct()
    servicios_ventas = ventas_filtradas.filter(detalleventamanual_set__servicio__isnull=False).distinct()

    # Paginación independiente para productos y servicios
    paginator_productos = Paginator(productos_ventas, 5)
    paginator_servicios = Paginator(servicios_ventas, 5)

    page_productos = request.GET.get('page_productos')
    page_servicios = request.GET.get('page_servicios')

    try:
        ventas_productos_paginadas = paginator_productos.page(page_productos)
    except PageNotAnInteger:
        ventas_productos_paginadas = paginator_productos.page(1)
    except EmptyPage:
        ventas_productos_paginadas = paginator_productos.page(paginator_productos.num_pages)

    try:
        ventas_servicios_paginadas = paginator_servicios.page(page_servicios)
    except PageNotAnInteger:
        ventas_servicios_paginadas = paginator_servicios.page(1)
    except EmptyPage:
        ventas_servicios_paginadas = paginator_servicios.page(paginator_servicios.num_pages)

    ventas_productos_list = []
    ventas_servicios_list = []

    for venta in ventas_productos_paginadas:
        productos = venta.detalleventamanual_set.filter(producto__isnull=False)

        venta.total_formateado = formato_precio(venta.total)
        venta.pago_cliente_formateado = formato_precio(venta.pago_cliente)
        venta.cambio_formateado = formato_precio(venta.cambio)

        total_ganancia_productos = 0
        productos_formateados = []

        for detalle in productos:
            producto = detalle.producto
            ganancia_producto = 0
            dias_transcurridos = ""
            stock_propio = "Sí" if producto.consignado else "No"

            if producto.fecha_adquisicion and venta.fecha_pago_final:
                dias_transcurridos = (venta.fecha_pago_final.date() - producto.fecha_adquisicion).days

            print(f"\nDEPURACIÓN - Producto en Venta Manual:")
            print(f"Nombre: {producto.nombre}")
            print(f"Stock Propio: {stock_propio}")
            print(f"Fecha Adquisición: {producto.fecha_adquisicion}")
            print(f"Fecha Pago Final: {venta.fecha_pago_final}")
            print(f"Días Transcurridos entre la Adquisición y Venta: {dias_transcurridos}")

            # Corrección: Si la venta aún no está pagada completamente, la ganancia debe ser 0
            if venta.fecha_pago_final:
                if producto.consignado:
                    if producto.precio_costo is not None and producto.costo_extra is not None:
                        ganancia_producto = producto.precio - producto.precio_costo - producto.costo_extra
                else:
                    if producto.porcentaje_consignacion is not None:
                        ganancia_producto = producto.precio * (producto.porcentaje_consignacion / 100)

            total_ganancia_productos += ganancia_producto

            productos_formateados.append({
                'nombre': producto.nombre,
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(producto.precio),
                'precio_costo': formato_precio(producto.precio_costo),
                'costo_extra': formato_precio(producto.costo_extra),
                'ganancia_producto': formato_precio(ganancia_producto),
                'dias_transcurridos': dias_transcurridos,
                'stock_propio': stock_propio
            })

        print(f"\nTOTAL GANANCIAS PRODUCTOS EN ESTA VENTA: {total_ganancia_productos}")

        ventas_productos_list.append({
            'venta': venta,
            'productos': productos_formateados,
            'ganancia_perdida': formato_precio(total_ganancia_productos),
        })

    for venta in ventas_servicios_paginadas:
        servicios = venta.detalleventamanual_set.filter(servicio__isnull=False)

        venta.total_formateado = formato_precio(venta.total)
        venta.pago_cliente_formateado = formato_precio(venta.pago_cliente)
        venta.cambio_formateado = formato_precio(venta.cambio)

        total_ganancia_servicios = 0
        servicios_formateados = []

        for detalle in servicios:
            precio = (
                formato_precio(detalle.servicio.precio)
                if detalle.servicio.precio > 0
                else formato_precio(venta.precio_personalizado or 0)
            )

            # Si la venta aún no está pagada completamente, la ganancia debe ser 0
            if venta.fecha_pago_final and venta.pago_cliente >= venta.total:
                ganancia_servicio = venta.total - (detalle.precio_costo or 0)
            else:
                ganancia_servicio = 0

            total_ganancia_servicios += ganancia_servicio

            servicios_formateados.append({
                'nombre': detalle.servicio.nombre,
                'precio_formateado': precio,
                'precio_costo': formato_precio(detalle.precio_costo),
                'ganancia_servicio': formato_precio(ganancia_servicio),
                'dias_transcurridos': "",  # No aplica para servicios
                'stock_propio': ""  # No aplica para servicios
            })

        print(f"TOTAL GANANCIA SERVICIOS EN ESTA VENTA: {total_ganancia_servicios}")

        ventas_servicios_list.append({
            'venta': venta,
            'servicios': servicios_formateados,
            'ganancia_perdida': formato_precio(total_ganancia_servicios),
        })

    return render(request, 'Transaccion/listar_ventas_manuales.html', {
        'ventas_productos_list': ventas_productos_list,
        'ventas_servicios_list': ventas_servicios_list,
        'ventas_productos_paginadas': ventas_productos_paginadas,
        'ventas_servicios_paginadas': ventas_servicios_paginadas,
        'cliente_query': cliente_query,
    })

@user_passes_test(es_administrador, login_url='home')
def agregar_venta_manual_producto(request):
    """
    Permite agregar una nueva venta manual de productos asociada a un cliente anónimo.
    """

    # Configurar el logger
    logger = logging.getLogger("ventas_manuales_productos")

    orden_compra_form = VentaManualForm(request.POST or None)
    detalle_producto_form = DetalleVentaManualProductoForm(request.POST or None)
    cliente_anonimo_form = ClienteAnonimoForm(request.POST or None)

    if request.method == 'POST':
        if (
            orden_compra_form.is_valid()
            and detalle_producto_form.is_valid()
            and cliente_anonimo_form.is_valid()
        ):
            # Obtener el producto (ya devuelve un objeto Producto)
            producto = detalle_producto_form.cleaned_data.get('producto')

            precio_costo = producto.precio_costo or 0
            precio_venta = producto.precio  # Cantidad siempre es 1, no es necesario multiplicar
            total_venta = precio_venta

            # Obtener la fecha de la transacción ingresada
            fecha_venta = orden_compra_form.cleaned_data.get('fecha_creacion')
            fecha_pago_final = orden_compra_form.cleaned_data.get('fecha_pago_final', None)

            # Validar el monto del pago
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)
            if pago_cliente > total_venta:
                messages.error(request, 'El monto del pago no puede ser mayor al total.')
                return render(request, 'Transaccion/agregar_venta_manual_producto.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_producto_form': detalle_producto_form,
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
                orden_compra.fecha_creacion = fecha_venta  # Guardar la fecha ingresada
                orden_compra.cambio = max(pago_cliente - total_venta, 0)

                # Registrar la fecha de pago final solo si el usuario la ingresa
                if pago_cliente >= total_venta and fecha_pago_final:
                    orden_compra.fecha_pago_final = fecha_pago_final
                else:
                    orden_compra.fecha_pago_final = None

                orden_compra.save()

                # Guardar el detalle del producto
                detalle = detalle_producto_form.save(commit=False)
                detalle.orden_compra = orden_compra
                detalle.precio_costo = precio_costo
                detalle.subtotal = precio_venta
                detalle.cantidad = 1  # Cantidad siempre es 1
                detalle.save()

                # Registrar log de la venta
                usuario = request.user
                logger.info(f"Nueva venta agregada por: {usuario.first_name} {usuario.last_name} ({usuario.email})")

                logger.info(
                    f"Detalles:\n"
                    f"ID de la Venta: {orden_compra.id}\n"
                    f"Nombre: {cliente_anonimo.nombre} {cliente_anonimo.apellido}\n"
                    f"Correo: {cliente_anonimo.email}\n"
                    f"Teléfono: {cliente_anonimo.numero_telefono or 'No especificado'}\n"
                    f"ID del Producto: {producto.id}\n"
                    f"Fecha de la Venta: {fecha_venta.strftime('%d-%m-%Y %H:%M')}\n"
                    f"Total (IVA incluido): ${orden_compra.total}\n"
                    f"Monto Pagado por el Cliente: ${pago_cliente}\n"
                    f"Fecha Pago Completo: {fecha_pago_final.strftime('%d-%m-%Y %H:%M') if fecha_pago_final else 'No especificada'}"
                )

            messages.success(request, 'Venta de producto registrada exitosamente.')
            return redirect('listar_ventas_manuales')

        # Mostrar errores si alguno de los formularios no es válido
        print("Errores en orden_compra_form:", orden_compra_form.errors)
        print("Errores en detalle_producto_form:", detalle_producto_form.errors)
        print("Errores en cliente_anonimo_form:", cliente_anonimo_form.errors)

    # Contexto para renderizar el formulario
    context = {
        'orden_compra_form': orden_compra_form,
        'detalle_producto_form': detalle_producto_form,
        'cliente_anonimo_form': cliente_anonimo_form,
    }
    return render(request, 'Transaccion/agregar_venta_manual_producto.html', context)

@user_passes_test(es_administrador, login_url='home')
def editar_venta_manual_producto(request, venta_id):
    """
    Permite editar una venta manual de productos, actualizando el precio de costo y el pago del cliente,
    manteniendo intacto el precio total de la venta.
    """

    # Configurar el logger
    logger = logging.getLogger("ventas_manuales_productos")
                           
    venta = get_object_or_404(VentaManual, id=venta_id)
    detalle_producto = venta.detalleventamanual_set.filter(producto__isnull=False).first()

    if not detalle_producto:
        messages.error(request, "Esta venta no está asociada a un producto.")
        return redirect('listar_ventas_manuales')

    usuario = request.user  # Obtener usuario que edita la venta

    # Guardar valores originales antes de la edición
    valores_anteriores = {
        "pago_cliente": venta.pago_cliente,
        "fecha_pago_final": venta.fecha_pago_final.strftime('%d-%m-%Y %H:%M') if venta.fecha_pago_final else 'No especificada',
        "precio_costo": detalle_producto.precio_costo,
        "subtotal": detalle_producto.subtotal,
    }

    orden_compra_form = VentaManualForm(request.POST or None, instance=venta)
    detalle_producto_form = DetalleVentaManualProductoForm(request.POST or None, instance=detalle_producto)

    if request.method == 'POST':
        print("POST recibido:", request.POST)

        if orden_compra_form.is_valid() and detalle_producto_form.is_valid():
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)
            total_venta = venta.total

            if pago_cliente > total_venta:
                messages.error(request, 'El monto del pago no puede ser mayor al total.')
                return render(request, 'Transaccion/editar_venta_manual_producto.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_producto_form': detalle_producto_form,
                    'venta': venta,
                })

            with transaction.atomic():
                # Guardar cambios en el detalle del producto
                detalle_actualizado = detalle_producto_form.save(commit=False)
                detalle_actualizado.save()

                # Guardar cambios en la venta
                venta_actualizada = orden_compra_form.save(commit=False)

                if venta_actualizada.pago_cliente >= (venta_actualizada.total or 0):
                    venta_actualizada.fecha_pago_final = orden_compra_form.cleaned_data.get('fecha_pago_final', None)
                else:
                    venta_actualizada.fecha_pago_final = None

                venta_actualizada.save()

                # Guardar valores nuevos después de la edición
                valores_nuevos = {
                    "pago_cliente": venta_actualizada.pago_cliente,
                    "fecha_pago_final": venta_actualizada.fecha_pago_final.strftime('%d-%m-%Y %H:%M') if venta_actualizada.fecha_pago_final else 'No especificada',
                    "precio_costo": detalle_actualizado.precio_costo,
                    "subtotal": detalle_actualizado.subtotal,
                }

                # Detectar cambios en los datos
                cambios = []
                for campo, valor_anterior in valores_anteriores.items():
                    valor_nuevo = valores_nuevos[campo]
                    if valor_anterior != valor_nuevo:
                        cambios.append(f"{campo}: {valor_anterior} -> {valor_nuevo}")

                if cambios:
                    logger.info(
                        f"Venta editada por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
                        f"ID de la Venta: {venta.id}\n"
                        + "\n".join(cambios)
                    )

            messages.success(request, 'Venta de producto actualizada correctamente.')
            return redirect('listar_ventas_manuales')

        else:
            print("Errores en los formularios:")
            print("Orden compra form:", orden_compra_form.errors)
            print("Detalle producto form:", detalle_producto_form.errors)
            messages.error(request, 'Errores en el formulario de edición.')

    return render(request, 'Transaccion/editar_venta_manual_producto.html', {
        'orden_compra_form': orden_compra_form,
        'detalle_producto_form': detalle_producto_form,
        'venta': venta,
    })

@user_passes_test(es_administrador, login_url='home')
def agregar_venta_manual_servicio(request):
    """
    Permite agregar una nueva venta manual de servicios asociada a un cliente anónimo.
    """

    # Configurar el logger
    logger = logging.getLogger("ventas_manuales_servicios")

    orden_compra_form = VentaManualForm(request.POST or None)
    detalle_servicio_form = DetalleVentaManualServicioForm(request.POST or None)
    cliente_anonimo_form = ClienteAnonimoForm(request.POST or None)

    if request.method == 'POST':
        if (
            orden_compra_form.is_valid()
            and detalle_servicio_form.is_valid()
            and cliente_anonimo_form.is_valid()
        ):
            # Obtener el servicio
            servicio = detalle_servicio_form.cleaned_data.get('servicio')
            precio_costo = detalle_servicio_form.cleaned_data.get('precio_costo', 0)

            # Calcular el total
            total_servicios = servicio.precio if servicio else 0
            precio_personalizado = orden_compra_form.cleaned_data.get('precio_personalizado', 0)
            total_venta = max(total_servicios, precio_personalizado)

            # Obtener la fecha de la transacción ingresada
            fecha_venta = orden_compra_form.cleaned_data.get('fecha_creacion')
            fecha_pago_final = orden_compra_form.cleaned_data.get('fecha_pago_final', None)

            # Validar el monto del pago
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)
            if pago_cliente > total_venta:
                messages.error(request, 'El monto del pago no puede ser mayor al total.')
                return render(request, 'Transaccion/agregar_venta_manual_servicio.html', {
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

                if pago_cliente >= total_venta and fecha_pago_final:
                    orden_compra.fecha_pago_final = fecha_pago_final
                else:
                    orden_compra.fecha_pago_final = None

                orden_compra.save()

                # Guardar el detalle del servicio
                detalle = detalle_servicio_form.save(commit=False)
                detalle.orden_compra = orden_compra
                detalle.cantidad = 1  # Siempre será 1 para servicios
                detalle.save()

                # Registrar logs
                usuario = request.user
                logger.info(f"Nueva venta agregada por: {usuario.first_name} {usuario.last_name} ({usuario.email})")

                logger.info(
                    f"Detalles:\n"
                    f"ID de la Venta: {orden_compra.id}\n"
                    f"Nombre: {cliente_anonimo.nombre} {cliente_anonimo.apellido}\n"
                    f"Correo: {cliente_anonimo.email}\n"
                    f"Teléfono: {cliente_anonimo.numero_telefono or 'No especificado'}\n"
                    f"Fecha de la Venta: {fecha_venta.strftime('%d-%m-%Y %H:%M')}\n"
                    f"ID del Servicio: {servicio.id if servicio else 'No especificado'}\n"
                    f"Valor de Compra: ${precio_costo}\n"
                    f"Total (IVA incluido): ${orden_compra.total}\n"
                    f"Monto Pagado por el Cliente: ${pago_cliente}\n"
                    f"Fecha Pago Completo: {fecha_pago_final.strftime('%d-%m-%Y %H:%M') if fecha_pago_final else 'No especificada'}"
                )

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
    return render(request, 'Transaccion/agregar_venta_manual_servicio.html', context)

@user_passes_test(es_administrador, login_url='home')
def editar_venta_manual_servicio(request, venta_id):
    """
    Permite editar una venta manual de servicios, actualizando el precio de costo y el pago del cliente,
    manteniendo intacto el precio personalizado.
    """

    # Configurar el logger
    logger = logging.getLogger("ventas_manuales_servicios")

    venta = get_object_or_404(VentaManual, id=venta_id)
    detalle_servicio = venta.detalleventamanual_set.filter(servicio__isnull=False).first()

    if not detalle_servicio:
        messages.error(request, "Esta venta no está asociada a un servicio.")
        return redirect('listar_ventas_manuales')

    usuario = request.user  # Usuario que realiza la edición

    # Guardar valores originales antes de la edición
    valores_anteriores = {
        "pago_cliente": venta.pago_cliente,
        "fecha_pago_final": venta.fecha_pago_final.strftime('%d-%m-%Y %H:%M') if venta.fecha_pago_final else 'No especificada',
        "precio_costo": detalle_servicio.precio_costo,
        "subtotal": detalle_servicio.subtotal,
    }

    orden_compra_form = VentaManualForm(request.POST or None, instance=venta)
    detalle_servicio_form = DetalleVentaManualServicioForm(request.POST or None, instance=detalle_servicio)

    if request.method == 'POST':
        print("POST recibido:", request.POST)

        if orden_compra_form.is_valid() and detalle_servicio_form.is_valid():
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)
            total_venta = venta.total

            if pago_cliente > total_venta:
                messages.error(request, 'El monto del pago no puede ser mayor al total.')
                return render(request, 'Transaccion/editar_venta_manual_servicio.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_servicio_form': detalle_servicio_form,
                    'venta': venta,
                })

            with transaction.atomic():
                # Guardar cambios en el detalle del servicio
                detalle_actualizado = detalle_servicio_form.save(commit=False)
                detalle_actualizado.save()

                # Guardar cambios en la venta
                venta_actualizada = orden_compra_form.save(commit=False)

                if venta_actualizada.pago_cliente >= (venta_actualizada.total or 0):
                    venta_actualizada.fecha_pago_final = orden_compra_form.cleaned_data.get('fecha_pago_final', None)
                else:
                    venta_actualizada.fecha_pago_final = None

                venta_actualizada.save()

                # Guardar valores nuevos después de la edición
                valores_nuevos = {
                    "pago_cliente": venta_actualizada.pago_cliente,
                    "fecha_pago_final": venta_actualizada.fecha_pago_final.strftime('%d-%m-%Y %H:%M') if venta_actualizada.fecha_pago_final else 'No especificada',
                    "precio_costo": detalle_actualizado.precio_costo,
                    "subtotal": detalle_actualizado.subtotal,
                }

                # Detectar cambios en los datos
                cambios = []
                for campo, valor_anterior in valores_anteriores.items():
                    valor_nuevo = valores_nuevos[campo]
                    if valor_anterior != valor_nuevo:
                        cambios.append(f"{campo}: {valor_anterior} -> {valor_nuevo}")

                if cambios:
                    logger.info(
                        f"Venta editada por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
                        f"ID de la Venta: {venta.id}\n"
                        + "\n".join(cambios)
                    )

            messages.success(request, 'Venta de servicio actualizada correctamente.')
            return redirect('listar_ventas_manuales')

        else:
            print("Errores en los formularios:")
            print("Orden compra form:", orden_compra_form.errors)
            print("Detalle servicio form:", detalle_servicio_form.errors)
            messages.error(request, 'Errores en el formulario de edición.')

    return render(request, 'Transaccion/editar_venta_manual_servicio.html', {
        'orden_compra_form': orden_compra_form,
        'detalle_servicio_form': detalle_servicio_form,
        'venta': venta,
    })
