from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.
from datetime import datetime  # Importa solo la clase datetime

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

# Diccionario de meses en español
MES_ESPANOL = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

def generar_grafico_base64(datos):
    """
    Genera un gráfico de torta a partir de datos proporcionados y lo convierte en
    una imagen base64 para su inclusión en reportes PDF.
    """
    fig, ax = plt.subplots()
    ax.pie(datos['values'], labels=datos['labels'], autopct='%1.1f%%')
    plt.axis('equal')
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    graphic = base64.b64encode(image_png)
    graphic = graphic.decode('utf-8')
    return graphic

def calcular_rango_fechas(anio, tipo, valor):
    """
    Calcula el rango de fechas basado en el tipo de filtro (mes, trimestre, semestre o anual).
    """
    if tipo == 'mes':
        fecha_inicio = datetime(anio, valor, 1)
        fecha_fin = datetime(anio, valor + 1, 1) if valor < 12 else datetime(anio + 1, 1, 1)
    
    elif tipo == 'trimestre':
        fecha_inicio = datetime(anio, 3 * (valor - 1) + 1, 1)
        mes_fin = 3 * valor
        fecha_fin = datetime(anio, mes_fin + 1, 1) if mes_fin < 12 else datetime(anio + 1, 1, 1)
    
    elif tipo == 'semestre':
        fecha_inicio = datetime(anio, 6 * (valor - 1) + 1, 1)
        mes_fin = 6 * valor
        fecha_fin = datetime(anio, mes_fin + 1, 1) if mes_fin < 12 else datetime(anio + 1, 1, 1)

    elif tipo == 'anual':
        fecha_inicio = datetime(anio, 1, 1)
        fecha_fin = datetime(anio + 1, 1, 1)

    return fecha_inicio, fecha_fin

def top_cinco_productos_manuales(anio, mes):
    """
    Retorna los cinco productos más vendidos en un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Producto.objects.filter(detalleventamanual__orden_compra__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

def top_cinco_servicios_manuales(anio, mes):
    """
    Retorna los cinco servicios más vendidos en un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Servicio.objects.filter(detalleventamanual__orden_compra__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

@user_passes_test(es_administrador, login_url='home')
def reporte_ventas_manuales(request):
    """
    Genera el contexto para la vista de reportes de ventas manuales.
    """

    anio_actual = datetime.now().year
    mes_actual = datetime.now().month

    anio = int(request.GET.get('anio', anio_actual))
    tipo_filtro = request.GET.get('tipo_filtro', 'mes')  # 'mes', 'trimestre', 'semestre', 'anual'
    valor_filtro = int(request.GET.get('valor_filtro', mes_actual)) if tipo_filtro != 'anual' else None

    fecha_inicio, fecha_fin = calcular_rango_fechas(anio, tipo_filtro, valor_filtro)
    fecha_inicio = make_aware(fecha_inicio)
    fecha_fin = make_aware(fecha_fin)

    ventas = VentaManual.objects.filter(fecha_pago_final__range=[fecha_inicio, fecha_fin])

    total_ganancias = 0
    total_productos = 0
    total_servicios = 0

    for venta in ventas:
        productos = venta.detalleventamanual_set.filter(producto__isnull=False)
        servicios = venta.detalleventamanual_set.filter(servicio__isnull=False)

        total_ganancia_productos = 0
        total_ganancia_servicios = 0

        # Cálculo de productos
        for detalle in productos:
            producto = detalle.producto
            ganancia_producto = 0

            '''
            print(f"\nDEPURACIÓN - Producto en Reporte:")
            print(f"Nombre: {producto.nombre}")
            print(f"Stock Propio: {producto.consignado}")
            print(f"Precio Venta: {producto.precio}")
            print(f"Valor de Compra: {producto.precio_costo}")
            print(f"Costo Extra: {producto.costo_extra}")
            print(f"Porcentaje Consignación: {producto.porcentaje_consignacion}") '''

            if producto.consignado:  # Stock Propio = Sí
                if producto.precio_costo is not None and producto.costo_extra is not None:
                    ganancia_producto = producto.precio - producto.precio_costo - producto.costo_extra
                else:
                    ganancia_producto = 0
            else:  # Stock Propio = No (Consignado)
                if producto.porcentaje_consignacion is not None:
                    ganancia_producto = producto.precio * (producto.porcentaje_consignacion / 100)
                else:
                    ganancia_producto = 0

            total_ganancia_productos += ganancia_producto

        # print(f"TOTAL GANANCIAS PRODUCTOS EN ESTA VENTA: {total_ganancia_productos}")

        # Cálculo de servicios
        for detalle in servicios:
            ganancia_servicio = 0

            if venta.pago_cliente >= venta.total:
                ganancia_servicio = venta.total - (detalle.precio_costo or 0)
            else:
                ganancia_servicio = 0  # Mantener en 0 hasta completar el pago

            total_ganancia_servicios += ganancia_servicio

            '''
            print(f"\nDEPURACIÓN - Servicio en Reporte:")
            print(f"Nombre: {detalle.servicio.nombre}")
            print(f"Precio Servicio: {detalle.servicio.precio}")
            print(f"Precio Costo: {detalle.precio_costo}")
            print(f"Pago Cliente: {venta.pago_cliente}")
            print(f"Total Venta: {venta.total}")
            print(f"Ganancia Servicio Calculada: {ganancia_servicio}") '''

        # print(f"TOTAL GANANCIA SERVICIOS EN ESTA VENTA: {total_ganancia_servicios}")

        # Sumamos la ganancia total
        total_ganancias += total_ganancia_productos + total_ganancia_servicios
        total_productos += productos.count()
        total_servicios += servicios.count()

    total_ganancias_formateado = formato_precio(total_ganancias)

    top_cinco_productos = Producto.objects.filter(
        detalleventamanual__orden_compra__fecha_pago_final__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

    top_cinco_servicios = Servicio.objects.filter(
        detalleventamanual__orden_compra__fecha_pago_final__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

    mensaje_productos = "No se han registrado ventas de productos." if not top_cinco_productos else ""
    mensaje_servicios = "No se han registrado ventas de servicios." if not top_cinco_servicios else ""

    datos_productos = json.dumps({
        'labels': [producto.nombre for producto in top_cinco_productos],
        'data': [producto.total_vendido for producto in top_cinco_productos]
    }, cls=DjangoJSONEncoder) if top_cinco_productos else json.dumps({})

    datos_servicios = json.dumps({
        'labels': [servicio.nombre for servicio in top_cinco_servicios],
        'data': [servicio.total_vendido for servicio in top_cinco_servicios]
    }, cls=DjangoJSONEncoder) if top_cinco_servicios else json.dumps({})

    nombre_mes = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                  5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                  9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                  }.get(valor_filtro, "Anual") if tipo_filtro != 'anual' else "Anual"

    datos_grafico = {
        'labels': [producto.nombre for producto in top_cinco_productos],
        'values': [producto.total_vendido for producto in top_cinco_productos]
    }
    imagen_grafico = generar_grafico_base64(datos_grafico)

    contexto = {
        'datos_productos_json': datos_productos,
        'datos_servicios_json': datos_servicios,
        'total_productos': total_productos,
        'total_servicios': total_servicios,
        'total_ganancias_formateado': total_ganancias_formateado,
        'mensaje_productos': mensaje_productos,
        'mensaje_servicios': mensaje_servicios,
        'rango_anios': range(2022, 2028),
        'anio_actual': anio_actual,
        'anio_seleccionado': anio,
        'tipo_filtro': tipo_filtro,
        'valor_filtro': valor_filtro,
        'nombre_mes': nombre_mes,
        'imagen_grafico': imagen_grafico,
        'top_cinco_productos': top_cinco_productos,
        'top_cinco_servicios': top_cinco_servicios,
    }

    return render(request, 'Transaccion/reporte_ventas_manuales.html', contexto)

def top_cinco_productos_online(anio, mes):
    """
    Retorna los cinco productos más vendidos en ventas online para un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)

    return Producto.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]
    ).annotate(
        total_vendido=Sum('detalleventaonline__cantidad')
    ).order_by('-total_vendido')[:5]

def top_cinco_servicios_online(anio, mes):
    """
    Retorna los cinco servicios más vendidos en ventas online para un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)

    return Servicio.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]
    ).annotate(
        total_vendido=Sum('detalleventaonline__cantidad')
    ).order_by('-total_vendido')[:5]

@user_passes_test(es_administrador, login_url='home')
def reporte_ventas_online(request):
    """
    Genera el contexto para el reporte de ventas online.
    Permite filtrar por mes, trimestre, semestre o anual.
    """
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month

    # Obtener parámetros del GET (filtro dinámico)
    anio = int(request.GET.get('anio', anio_actual))
    tipo_filtro = request.GET.get('tipo_filtro', 'mes')  # 'mes', 'trimestre', 'semestre', 'anual'
    valor_filtro = int(request.GET.get('valor_filtro', mes_actual)) if tipo_filtro != 'anual' else None

    # Calcular rango de fechas según el filtro
    fecha_inicio, fecha_fin = calcular_rango_fechas(anio, tipo_filtro, valor_filtro)

    # Calcular el total general de ventas (productos y servicios)
    total_productos = Producto.objects.filter(
        detalleventaonline__fecha_estado_final__range=[fecha_inicio, fecha_fin],  # Usar fecha de actualización
        detalleventaonline__estado_reserva="Vendida"  # Filtrar productos vendidos
    ).aggregate(total_vendido=Sum('detalleventaonline__cantidad'))['total_vendido'] or 0

    total_servicios = Servicio.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]  # Fecha original para servicios
    ).aggregate(total_vendido=Sum('detalleventaonline__cantidad'))['total_vendido'] or 0

    # Calcular total de ganancias
    detalles = DetalleVentaOnline.objects.filter(
        Q(producto__isnull=False, fecha_estado_final__range=[fecha_inicio, fecha_fin], estado_reserva="Vendida") | 
        Q(servicio__isnull=False, orden_compra__fecha__range=[fecha_inicio, fecha_fin])
    )

    total_ganancias = 0  # Inicializar total de ganancias

    for detalle in detalles:
        ganancia_detalle = 0

        if detalle.producto:
            producto = detalle.producto

            '''
            print("\n--- DEBUG: Producto en Reporte ---")
            print(f"Nombre: {producto.nombre}")
            print(f"Stock Propio: {producto.consignado}")  # Mensaje más claro
            print(f"Precio Venta: {producto.precio}")
            print(f"Valor de Compra: {producto.precio_costo}")
            print(f"Costo Extra: {producto.costo_extra}")
            print(f"Porcentaje Consignación: {producto.porcentaje_consignacion}")
            print(f"Estado de Reserva: {detalle.estado_reserva}") '''

            # Validamos si el producto fue vendido
            if detalle.estado_reserva == "Vendida":
                # AHORA SE CALCULA CORRECTAMENTE: STOCK PROPIO
                if producto.consignado:  # Ahora se calcula bien como STOCK PROPIO
                    if producto.precio_costo is not None and producto.costo_extra is not None:
                        ganancia_detalle = (producto.precio - (producto.precio_costo + producto.costo_extra)) * detalle.cantidad
                        # print(f"Ganancia Calculada (Stock Propio): {ganancia_detalle}")
                    else:
                        ganancia_detalle = 0
                        # print("Faltan valores de costo o extra. Ganancia = 0")
                else:  # Producto consignado
                    if producto.porcentaje_consignacion is not None:
                        ganancia_detalle = (producto.precio * (producto.porcentaje_consignacion / 100)) * detalle.cantidad
                        # print(f"Ganancia Calculada (Consignación): {ganancia_detalle}")
                    else:
                        ganancia_detalle = 0  # Producto consignado sin porcentaje
                        # print("Producto consignado sin porcentaje definido. Ganancia = 0")

        elif detalle.servicio:
            ganancia_detalle = detalle.precio * detalle.cantidad
            '''
            print("\n--- DEBUG: Servicio en Reporte ---")
            print(f"Nombre: {detalle.servicio.nombre}")
            print(f"Precio: {detalle.precio}")
            print(f"Cantidad: {detalle.cantidad}")
            print(f"Ganancia Calculada (Servicio): {ganancia_detalle}") '''

        total_ganancias += ganancia_detalle

    # print(f"\nTOTAL GANANCIAS CALCULADAS: {total_ganancias}\n")

    # Formatear el total de ganancias para el reporte
    total_ganancias_formateado = formato_precio(total_ganancias)

    # Obtener datos de ventas online dentro del rango
    top_cinco_productos = Producto.objects.filter(
        detalleventaonline__fecha_estado_final__range=[fecha_inicio, fecha_fin],  # Usar fecha de actualización
        detalleventaonline__estado_reserva="Vendida"  # Solo productos vendidos
    ).annotate(total_vendido=Sum('detalleventaonline__cantidad')).order_by('-total_vendido')[:5]

    top_cinco_servicios = Servicio.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]  # Usar fecha de creación
    ).annotate(total_vendido=Sum('detalleventaonline__cantidad')).order_by('-total_vendido')[:5]

    # Mensajes si no hay productos o servicios vendidos
    mensaje_productos = ""
    mensaje_servicios = ""

    if not top_cinco_productos:
        filtro_texto = "año" if tipo_filtro == 'anual' else tipo_filtro
        mensaje_productos = f"No se han registrado ventas de productos online en el {filtro_texto} seleccionado."

    if not top_cinco_servicios:
        filtro_texto = "año" if tipo_filtro == 'anual' else tipo_filtro
        mensaje_servicios = f"No se han registrado ventas de servicios online en el {filtro_texto} seleccionado."

    # Preparar datos para gráficos (JSON)
    datos_productos = json.dumps({
        'labels': [producto.nombre for producto in top_cinco_productos],
        'data': [producto.total_vendido for producto in top_cinco_productos]
    }, cls=DjangoJSONEncoder) if top_cinco_productos else json.dumps({})

    datos_servicios = json.dumps({
        'labels': [servicio.nombre for servicio in top_cinco_servicios],
        'data': [servicio.total_vendido for servicio in top_cinco_servicios]
    }, cls=DjangoJSONEncoder) if top_cinco_servicios else json.dumps({})

    # Meses para visualización
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    # Trimestres, semestres y filtro anual para mostrar en el filtro
    trimestres = {1: '1er Trimestre', 2: '2do Trimestre', 3: '3er Trimestre', 4: '4to Trimestre'}
    semestres = {1: '1er Semestre', 2: '2do Semestre'}

    nombre_mes = meses.get(valor_filtro, "Mes desconocido") if tipo_filtro != 'anual' else "Anual"

    datos_grafico = {
        'labels': [producto.nombre for producto in top_cinco_productos],
        'values': [producto.total_vendido for producto in top_cinco_productos]
    }
    imagen_grafico = generar_grafico_base64(datos_grafico)

    # Contexto para la plantilla
    contexto = {
        'datos_productos_json': datos_productos,
        'datos_servicios_json': datos_servicios,
        'total_productos': total_productos,
        'total_servicios': total_servicios,
        'total_ganancias_formateado': total_ganancias_formateado,
        'mensaje_productos': mensaje_productos,
        'mensaje_servicios': mensaje_servicios,
        'rango_anios': range(2022, 2028),
        'rango_meses': range(1, 13),
        'rango_trimestres': range(1, 5),
        'rango_semestres': range(1, 3),
        'anio_actual': anio_actual,
        'mes_actual': mes_actual,
        'anio_seleccionado': anio,
        'tipo_filtro': tipo_filtro,
        'valor_filtro': valor_filtro,
        'nombre_mes': nombre_mes,
        'imagen_grafico': imagen_grafico,
        'top_cinco_productos': top_cinco_productos,
        'top_cinco_servicios': top_cinco_servicios,
    }

    return render(request, 'Transaccion/reporte_ventas_online.html', contexto)
