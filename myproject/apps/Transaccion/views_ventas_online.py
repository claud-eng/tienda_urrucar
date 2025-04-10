from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.
from datetime import datetime

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

            ''' Mostrar datos del producto antes del cálculo
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
            print(f"Cantidad Vendida: {detalle.cantidad}") '''

            # Aplicar cálculo de ganancia solo si la reserva es "Vendida"
            if detalle.estado_reserva == "Vendida":
                if not producto.consignado:  
                    # Producto CONSIGNADO
                    if producto.porcentaje_consignacion is not None:
                        ganancia_detalle = round((producto.precio * (producto.porcentaje_consignacion / 100)) * detalle.cantidad, 2)
                        # print(f"Ganancia Calculada (Consignación, corregida): {ganancia_detalle}")
                    else:
                        print("Producto consignado pero sin porcentaje definido. Ganancia = 0")
                else:  
                    # Producto PROPIO (STOCK PROPIO)
                    if producto.precio_costo is not None and producto.costo_extra is not None:
                        ganancia_detalle = max((producto.precio - producto.precio_costo - producto.costo_extra) * detalle.cantidad, 0)
                        # print(f"Ganancia Calculada (Stock Propio, corregida): {ganancia_detalle}")
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

        # print(f"\nTOTAL GANANCIAS PRODUCTOS EN ESTA VENTA (Orden {venta.id}): {ganancia_total}")

        # Buscar la primera fecha_estado_final válida (para mostrar en la tabla)
        fecha_estado_final = next(
            (
                d.fecha_estado_final
                for d in venta.detalleventaonline_set.all()
                if d.producto and d.producto.categoria == "Vehículo" and d.fecha_estado_final
            ),
            None
        )

        # Buscar el primer valor de días desde adquisición
        dias_desde_adquisicion = next(
            (
                d.dias_desde_adquisicion
                for d in venta.detalleventaonline_set.all()
                if d.producto and d.producto.categoria == "Vehículo" and d.dias_desde_adquisicion is not None
            ),
            None
        )

        # Buscar el primer valor de cálculo de tiempo transcurrido
        calculo_tiempo_transcurrido = next(
            (
                d.calculo_tiempo_transcurrido
                for d in venta.detalleventaonline_set.all()
                if d.producto and d.producto.categoria == "Vehículo" and d.calculo_tiempo_transcurrido is not None
            ),
            None
        )

        ventas_productos_list.append({
            'venta': venta,
            'productos': productos_formateados,
            'ganancia_formateada': formato_precio(ganancia_total),
            'fecha_estado_final': fecha_estado_final,
            'dias_desde_adquisicion': f"{dias_desde_adquisicion} días" if dias_desde_adquisicion is not None else "---",
            'calculo_tiempo_transcurrido': f"{calculo_tiempo_transcurrido} días" if calculo_tiempo_transcurrido is not None else "---",
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
