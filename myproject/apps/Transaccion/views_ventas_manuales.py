from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.
from datetime import datetime

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

# Retorna productos filtrados por nombre y/o patente en formato JSON para autocompletado (máx. 10).
def buscar_productos(request):
    term = request.GET.get('term', '')
    productos = Producto.objects.filter(
        Q(nombre__icontains=term) | Q(patente__icontains=term)
    )[:10]

    resultados = [{
        'id': p.id,
        'label': f'{p.nombre} - {p.patente or "Sin patente"}',
        'value': f'{p.nombre} - {p.patente or "Sin patente"}'
    } for p in productos]

    return JsonResponse(resultados, safe=False)

# Lista ventas manuales de productos y servicios.
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

    ventas_filtradas = VentaManual.objects.filter(query).order_by('-id')

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

            '''
            print(f"\nDEPURACIÓN - Producto en Venta Manual:")
            print(f"Nombre: {producto.nombre}")
            print(f"Stock Propio: {stock_propio}")
            print(f"Fecha Adquisición: {producto.fecha_adquisicion}")
            print(f"Fecha Pago Final: {venta.fecha_pago_final}")
            print(f"Días Transcurridos entre la Adquisición y Venta: {dias_transcurridos}") '''

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
                'patente': producto.patente or "", 
                'cantidad': detalle.cantidad,
                'precio_formateado': formato_precio(producto.precio),
                'precio_costo': formato_precio(producto.precio_costo),
                'costo_extra': formato_precio(producto.costo_extra),
                'ganancia_producto': formato_precio(ganancia_producto),
                'dias_transcurridos': dias_transcurridos,
                'stock_propio': stock_propio
            })

        # print(f"\nTOTAL GANANCIAS PRODUCTOS EN ESTA VENTA: {total_ganancia_productos}")

        total_real = venta.total or venta.calcular_total()

        estado_pago = (
            "Cancelado"
            if venta.pago_cliente >= total_real
            else f"Pendiente: ${formato_precio(total_real - venta.pago_cliente)}"
        )

        ventas_productos_list.append({
            'venta': venta,
            'productos': productos_formateados,
            'ganancia_perdida': formato_precio(total_ganancia_productos),
            'estado_pago': estado_pago,
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
                'marca_vehiculo': detalle.marca_vehiculo or "",
                'modelo_vehiculo': detalle.modelo_vehiculo or "",
                'patente_vehiculo': detalle.patente_vehiculo or "",
                'dias_transcurridos': "",  # No aplica para servicios
                'stock_propio': ""  # No aplica para servicios
            })

        total_real = venta.total or venta.calcular_total()
        estado_pago = (
            "Cancelado"
            if venta.pago_cliente >= total_real
            else f"Pendiente: ${formato_precio(total_real - venta.pago_cliente)}"
        )

        ventas_servicios_list.append({
            'venta': venta,
            'servicios': servicios_formateados,
            'ganancia_perdida': formato_precio(total_ganancia_servicios),
            'estado_pago': estado_pago,
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

            # Validar consistencia entre monto pagado y fecha de pago final
            if pago_cliente < total_venta and fecha_pago_final:
                messages.error(request, 'No puedes ingresar una fecha de pago completo si el monto pagado no cubre el total del vehículo.')
                return render(request, 'Transaccion/agregar_venta_manual_producto.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_producto_form': detalle_producto_form,
                    'cliente_anonimo_form': cliente_anonimo_form,
                })
            
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
                detalle.producto = producto
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
                    f"RUT: {cliente_anonimo.rut or 'No especificado'}\n"
                    f"ID del Producto: {producto.id}\n"
                    f"Marca: {producto.marca}\n"
                    f"Modelo: {producto.modelo or 'No especificado'}\n"
                    f"Patente: {producto.patente or 'Sin Patente'}\n"
                    f"Fecha de la Venta: {fecha_venta.strftime('%d-%m-%Y %H:%M') if fecha_venta else 'No especificada'}\n"
                    f"Valor Total del Vehículo (IVA incluido): ${orden_compra.total}\n"
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
        "nombre": venta.cliente_anonimo.nombre,
        "apellido": venta.cliente_anonimo.apellido,
        "email": venta.cliente_anonimo.email,
        "numero_telefono": venta.cliente_anonimo.numero_telefono or 'No especificado',
        "rut": venta.cliente_anonimo.rut or 'No especificado',
        "marca": detalle_producto.producto.marca,
        "modelo": detalle_producto.producto.modelo or "No especificado",
        "patente": detalle_producto.producto.patente or "Sin Patente",
        "fecha_creacion": venta.fecha_creacion.strftime('%d-%m-%Y %H:%M') if venta.fecha_creacion else 'No especificada',
        "subtotal": detalle_producto.subtotal,
        "pago_cliente": venta.pago_cliente,
        "fecha_pago_final": venta.fecha_pago_final.strftime('%d-%m-%Y %H:%M') if venta.fecha_pago_final else 'No especificada',
        "precio_costo": detalle_producto.precio_costo,
    }

    orden_compra_form = VentaManualForm(request.POST or None, instance=venta)
    detalle_producto_form = DetalleVentaManualProductoForm(request.POST or None, instance=detalle_producto)
    cliente_anonimo_form = ClienteAnonimoForm(request.POST or None, instance=venta.cliente_anonimo)

    if request.method == 'POST':
        print("POST recibido:", request.POST)

        if orden_compra_form.is_valid() and detalle_producto_form.is_valid():
            producto_seleccionado = detalle_producto_form.cleaned_data.get('producto')
            
            # Usar el precio del producto seleccionado como total de la venta
            total_venta = producto_seleccionado.precio if producto_seleccionado else venta.total
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)

            # Validar consistencia entre monto pagado y fecha de pago final
            fecha_pago_final = orden_compra_form.cleaned_data.get('fecha_pago_final', None)

            if pago_cliente < total_venta and fecha_pago_final:
                messages.error(request, 'No puedes ingresar una fecha de pago completo si el monto pagado no cubre el total del vehículo.')
                return render(request, 'Transaccion/editar_venta_manual_producto.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_producto_form': detalle_producto_form,
                    'cliente_anonimo_form': cliente_anonimo_form,
                    'venta': venta,
                })

            if pago_cliente == total_venta and not fecha_pago_final:
                messages.error(request, 'Debes ingresar la fecha de pago completo si el monto pagado cubre el total del vehículo.')
                return render(request, 'Transaccion/editar_venta_manual_producto.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_producto_form': detalle_producto_form,
                    'cliente_anonimo_form': cliente_anonimo_form,
                    'venta': venta,
                })

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
                detalle_actualizado.producto = producto_seleccionado
                detalle_actualizado.save()

                print("Producto asignado:", producto_seleccionado)
                print("Precio producto:", producto_seleccionado.precio)

                # Guardar cliente
                cliente_anonimo_actualizado = cliente_anonimo_form.save()

                # Guardar cambios de la venta
                venta_actualizada = orden_compra_form.save(commit=False)
                venta_actualizada.precio_personalizado = producto_seleccionado.precio
                venta_actualizada.fecha_creacion = orden_compra_form.cleaned_data.get('fecha_creacion')
                venta_actualizada.pago_cliente = pago_cliente

                print("Precio personalizado actualizado:", venta_actualizada.precio_personalizado)
                print("Total estimado antes de guardar:", venta_actualizada.precio_personalizado)
                print("Pago del cliente:", pago_cliente)

                # Guardar venta inicialmente
                venta_actualizada.save()

                # Asignar fecha de pago final si corresponde y volver a guardar
                if pago_cliente >= (venta_actualizada.precio_personalizado or 0):
                    venta_actualizada.fecha_pago_final = fecha_pago_final
                else:
                    venta_actualizada.fecha_pago_final = None

                print("Fecha de pago final a guardar:", venta_actualizada.fecha_pago_final)

                venta_actualizada.save()

                # Refrescar la venta original desde la BD
                venta.refresh_from_db()

                # Guardar valores nuevos después de la edición
                valores_nuevos = {
                    "nombre": cliente_anonimo_actualizado.nombre,
                    "apellido": cliente_anonimo_actualizado.apellido,
                    "email": cliente_anonimo_actualizado.email,
                    "numero_telefono": cliente_anonimo_actualizado.numero_telefono or 'No especificado',
                    "rut": cliente_anonimo_actualizado.rut or 'No especificado',
                    "marca": detalle_actualizado.producto.marca,
                    "modelo": detalle_actualizado.producto.modelo or "No especificado",
                    "patente": detalle_actualizado.producto.patente or "Sin Patente",
                    "fecha_creacion": venta_actualizada.fecha_creacion.strftime('%d-%m-%Y %H:%M') if venta_actualizada.fecha_creacion else 'No especificada',
                    "subtotal": detalle_actualizado.subtotal,
                    "pago_cliente": venta_actualizada.pago_cliente,
                    "fecha_pago_final": venta_actualizada.fecha_pago_final.strftime('%d-%m-%Y %H:%M') if venta_actualizada.fecha_pago_final else 'No especificada',
                    "precio_costo": detalle_actualizado.precio_costo,
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
        'cliente_anonimo_form': cliente_anonimo_form,
        'venta': venta,
    })

# Retorna servicios filtrados por nombre en formato JSON para autocompletado (máx. 10).
def buscar_servicios(request):
    term = request.GET.get('term', '')
    servicios = Servicio.objects.filter(nombre__icontains=term)[:10]  # máximo 10 resultados
    resultados = [{'id': s.id, 'label': s.nombre, 'value': s.nombre} for s in servicios]
    return JsonResponse(resultados, safe=False)

@user_passes_test(es_administrador, login_url='home')
def agregar_venta_manual_servicio(request):
    """
    Permite agregar una nueva venta manual de servicios asociada a un cliente anónimo.
    """

    # Configurar el logger
    logger = logging.getLogger("ventas_manuales_servicios")

    orden_compra_form = VentaManualForm(request.POST or None)
    orden_compra_form.fields['precio_personalizado'].label = 'Valor de Servicio'
    if request.method != 'POST':
        orden_compra_form.fields['precio_personalizado'].initial = 0
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

            # Validar consistencia entre monto pagado y fecha de pago final
            if pago_cliente < total_venta and fecha_pago_final:
                messages.error(request, 'No puedes ingresar una fecha de pago completo si el monto pagado no cubre el total del servicio.')
                return render(request, 'Transaccion/agregar_venta_manual_servicio.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_servicio_form': detalle_servicio_form,
                    'cliente_anonimo_form': cliente_anonimo_form,
                })

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
                detalle.servicio = detalle_servicio_form.cleaned_data['servicio']
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
                    f"RUT: {cliente_anonimo.rut or 'No especificado'}\n"
                    f"Fecha de la Venta: {fecha_venta.strftime('%d-%m-%Y %H:%M') if fecha_venta else 'No especificada'}\n"
                    f"ID del Servicio: {servicio.id if servicio else 'No especificado'}\n"
                    f"Marca del Vehículo: {detalle.marca_vehiculo or 'No especificada'}\n"
                    f"Modelo del Vehículo: {detalle.modelo_vehiculo or 'No especificado'}\n"
                    f"Patente del Vehículo: {detalle.patente_vehiculo or 'No especificada'}\n"
                    f"Valor de Servicio: ${orden_compra.total}\n"
                    f"Valor Costo: ${precio_costo}\n"
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
    así como los datos del cliente anónimo y los datos del vehículo asociados al servicio.
    """

    # Configurar el logger
    logger = logging.getLogger("ventas_manuales_servicios")

    # Obtener la venta y su detalle de servicio asociado
    venta = get_object_or_404(VentaManual, id=venta_id)
    detalle_servicio = venta.detalleventamanual_set.filter(servicio__isnull=False).first()

    if not detalle_servicio:
        messages.error(request, "Esta venta no está asociada a un servicio.")
        return redirect('listar_ventas_manuales')

    usuario = request.user  # Usuario que realiza la edición

    # Guardar valores originales antes de la edición
    valores_anteriores = {
        "nombre": venta.cliente_anonimo.nombre,
        "apellido": venta.cliente_anonimo.apellido,
        "email": venta.cliente_anonimo.email,
        "numero_telefono": venta.cliente_anonimo.numero_telefono or 'No especificado',
        "rut": venta.cliente_anonimo.rut or 'No especificado',
        "valor_servicio": venta.total,
        "pago_cliente": venta.pago_cliente,
        "fecha_creacion": venta.fecha_creacion,
        "fecha_pago_final": venta.fecha_pago_final,
        "precio_costo": detalle_servicio.precio_costo,
        "subtotal": detalle_servicio.subtotal,
        "marca_vehiculo": detalle_servicio.marca_vehiculo or 'No especificada',
        "modelo_vehiculo": detalle_servicio.modelo_vehiculo or 'No especificado',
        "patente_vehiculo": detalle_servicio.patente_vehiculo or 'No especificada',
    }

    # Formularios con datos actuales de la venta
    orden_compra_form = VentaManualForm(request.POST or None, instance=venta)
    orden_compra_form.fields['precio_personalizado'].label = 'Valor de Servicio'

    detalle_servicio_form = DetalleVentaManualServicioForm(request.POST or None, instance=detalle_servicio)
    cliente_anonimo_form = ClienteAnonimoForm(request.POST or None, instance=venta.cliente_anonimo)

    if request.method == 'POST':
        print("POST recibido:", request.POST)

        # Validar los formularios
        if orden_compra_form.is_valid() and detalle_servicio_form.is_valid() and cliente_anonimo_form.is_valid():
            pago_cliente = orden_compra_form.cleaned_data.get('pago_cliente', 0)
            precio_personalizado = orden_compra_form.cleaned_data.get('precio_personalizado', 0)
            total_venta = precio_personalizado

            # Validar consistencia entre monto pagado y total
            if pago_cliente > total_venta:
                messages.error(request, 'El monto del pago no puede ser mayor al total.')
                return render(request, 'Transaccion/editar_venta_manual_servicio.html', {
                    'orden_compra_form': orden_compra_form,
                    'detalle_servicio_form': detalle_servicio_form,
                    'cliente_anonimo_form': cliente_anonimo_form,
                    'venta': venta,
                })

            with transaction.atomic():
                # Guardar cambios en el cliente anónimo
                cliente_anonimo_actualizado = cliente_anonimo_form.save()

                # Guardar cambios en el detalle del servicio
                detalle_actualizado = detalle_servicio_form.save(commit=False)
                detalle_actualizado.servicio = detalle_servicio_form.cleaned_data['servicio']  # Asignar el servicio desde el autocompletado
                detalle_actualizado.save()

                # Guardar cambios en la venta
                venta_actualizada = orden_compra_form.save(commit=False)
                venta_actualizada.cliente_anonimo = cliente_anonimo_actualizado
                venta_actualizada.total = total_venta

                # Obtener fecha desde el formulario
                fecha_pago_final = orden_compra_form.cleaned_data.get('fecha_pago_final', None)

                # Validar consistencia entre monto pagado y fecha de pago final
                if pago_cliente < total_venta and fecha_pago_final:
                    messages.error(request, 'No puedes ingresar una fecha de pago completo si el monto pagado no cubre el total del servicio.')
                    return render(request, 'Transaccion/editar_venta_manual_servicio.html', {
                        'orden_compra_form': orden_compra_form,
                        'detalle_servicio_form': detalle_servicio_form,
                        'cliente_anonimo_form': cliente_anonimo_form,
                        'venta': venta,
                    })

                # Corregir desfase horario si es naive
                if fecha_pago_final and timezone.is_naive(fecha_pago_final):
                    fecha_pago_final = timezone.make_aware(fecha_pago_final, timezone.get_current_timezone())

                print("Precio personalizado actual:", venta_actualizada.precio_personalizado)
                print("Pago cliente actual:", venta_actualizada.pago_cliente)
                print("¿Pago completo?", venta_actualizada.pago_cliente >= (venta_actualizada.precio_personalizado or 0))

                # Asignar la fecha solo si corresponde
                if venta_actualizada.pago_cliente >= (venta_actualizada.precio_personalizado or 0):
                    venta_actualizada.fecha_pago_final = fecha_pago_final
                else:
                    venta_actualizada.fecha_pago_final = None

                venta_actualizada.save()

                # Guardar valores nuevos después de la edición (mantener datetime como objeto)
                valores_nuevos = {
                    "nombre": cliente_anonimo_actualizado.nombre,
                    "apellido": cliente_anonimo_actualizado.apellido,
                    "email": cliente_anonimo_actualizado.email,
                    "numero_telefono": cliente_anonimo_actualizado.numero_telefono or 'No especificado',
                    "rut": cliente_anonimo_actualizado.rut or 'No especificado',
                    "valor_servicio": venta_actualizada.total,
                    "pago_cliente": venta_actualizada.pago_cliente,
                    "fecha_creacion": venta.fecha_creacion,
                    "fecha_pago_final": venta_actualizada.fecha_pago_final,
                    "precio_costo": detalle_actualizado.precio_costo,
                    "subtotal": detalle_actualizado.subtotal,
                    "marca_vehiculo": detalle_actualizado.marca_vehiculo or 'No especificada',
                    "modelo_vehiculo": detalle_actualizado.modelo_vehiculo or 'No especificado',
                    "patente_vehiculo": detalle_actualizado.patente_vehiculo or 'No especificada',
                }

                # Detectar cambios en los datos
                cambios = []
                for campo, valor_anterior in valores_anteriores.items():
                    valor_nuevo = valores_nuevos[campo]

                    # Comparar datetime de forma segura para evitar falsos positivos por zona horaria
                    if isinstance(valor_anterior, datetime) and isinstance(valor_nuevo, datetime):
                        naive_anterior = timezone.make_naive(valor_anterior, timezone.get_current_timezone())
                        naive_nuevo = timezone.make_naive(valor_nuevo, timezone.get_current_timezone())
                        if naive_anterior != naive_nuevo:
                            cambios.append(f"{campo}: {naive_anterior.strftime('%d-%m-%Y %H:%M')} -> {naive_nuevo.strftime('%d-%m-%Y %H:%M')}")
                    elif valor_anterior != valor_nuevo:
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
            print("Cliente anónimo form:", cliente_anonimo_form.errors)
            messages.error(request, 'Errores en el formulario de edición.')

    # Renderizar formulario con los datos actuales
    return render(request, 'Transaccion/editar_venta_manual_servicio.html', {
        'orden_compra_form': orden_compra_form,
        'detalle_servicio_form': detalle_servicio_form,
        'cliente_anonimo_form': cliente_anonimo_form,
        'venta': venta,
    })
