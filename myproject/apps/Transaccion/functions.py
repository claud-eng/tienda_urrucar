import base64  # Importa el módulo base64 para codificación y decodificación de datos.
import json  # Importa el módulo json para manejar datos en formato JSON.
import matplotlib.pyplot as plt  # Importa pyplot de matplotlib para crear gráficos.
from datetime import datetime, timedelta  # Importa datetime y timedelta para manejar fechas y tiempos.
from django.core.serializers.json import DjangoJSONEncoder  # Importa el codificador JSON específico de Django.
from django.db.models import Sum  # Importa Sum para realizar sumas agregadas en consultas de modelos.
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse  # Importa clases de respuesta y redirección HTTP.
from django.shortcuts import get_object_or_404, redirect, render  # Importa funciones de atajos para renderizar y redireccionar vistas.
from django.utils import timezone  # Importa el módulo timezone para manejar zonas horarias.
from io import BytesIO  # Importa BytesIO para manejo de flujos de datos en memoria.
from reportlab.lib import colors  # Importa colores de ReportLab para crear gráficos.
from reportlab.lib.pagesizes import letter  # Importa el tamaño de página 'letter' de ReportLab.
from reportlab.lib.utils import ImageReader  # Importa ImageReader de ReportLab para manejar imágenes en PDFs.
from reportlab.pdfgen import canvas  # Importa canvas de ReportLab para generar documentos PDF.
from reportlab.platypus import Table, TableStyle  # Importa Table y TableStyle de ReportLab para crear tablas en PDFs.
from .models import Carrito, DetalleVentaOnline, DetalleVentaManual, VentaOnline, VentaManual, Producto, Servicio  # Importa modelos de la aplicación actual.

# Diccionario de meses en español
MES_ESPANOL = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

def generar_comprobante_pdf_correo(orden):
    """
    Genera un PDF del comprobante de la orden de compra para enviar por correo.
    Incluye detalles del cliente, tipo de pago y productos comprados.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # Cabecera y datos principales de la orden
    p.drawString(100, 800, "Empresa: Automotriz Urrutia")
    p.drawString(100, 785, "Número de Orden: {}".format(orden.numero_orden))

    # Verificar si el cliente es autenticado o anónimo
    if orden.cliente:
        # Extraer nombre, apellido y correo del cliente autenticado
        nombre = orden.cliente.user.first_name if orden.cliente.user.first_name else "No disponible"
        apellido = orden.cliente.user.last_name if orden.cliente.user.last_name else ""
        correo = orden.cliente.user.username  # Username tratado como correo electrónico
        p.drawString(100, 770, "Cliente: {} {}".format(nombre, apellido))
        p.drawString(100, 755, "Correo: {}".format(correo))
    elif orden.cliente_anonimo:
        # Datos del cliente anónimo
        nombre = orden.cliente_anonimo.nombre if orden.cliente_anonimo.nombre else "Anónimo"
        apellido = orden.cliente_anonimo.apellido if orden.cliente_anonimo.apellido else ""
        p.drawString(100, 770, "Cliente: {} {}".format(nombre, apellido))
        p.drawString(100, 755, "Correo: {}".format(orden.cliente_anonimo.email))
    else:
        p.drawString(100, 770, "Cliente: Información no disponible")
        p.drawString(100, 755, "Correo: No disponible")

    # Fecha y hora de la orden
    fecha_local = timezone.localtime(orden.fecha)
    p.drawString(100, 740, "Fecha y Hora: {}".format(fecha_local.strftime("%d/%m/%Y %H:%M")))
    p.drawString(100, 725, "Detalle:")

    # Detalles de cada producto o servicio
    y = 710
    detalles = DetalleVentaOnline.objects.filter(orden_compra=orden)
    for detalle in detalles:
        producto_o_servicio = detalle.producto if detalle.producto else detalle.servicio
        p.drawString(
            120, y, 
            "{} - Cantidad: {} - Precio: ${}".format(
                producto_o_servicio.nombre, detalle.cantidad, detalle.precio
            )
        )
        y -= 15

        # Evitar que se salga de la página
        if y < 50:
            p.showPage()
            y = 800
            p.drawString(100, y, "Detalle (continuación):")
            y -= 15

    # Detalles del tipo de pago y el total
    tipo_pago_conversion = {
        'VD': 'Venta Débito',
        'VN': 'Venta Normal',
        'VC': 'Venta en Cuotas',
        'SI': '3 Cuotas sin Interés',
        'S2': '2 Cuotas sin Interés',
        'NC': 'N Cuotas sin Interés',
        'VP': 'Venta Prepago'
    }
    tipo_pago = tipo_pago_conversion.get(orden.tipo_pago, orden.tipo_pago)
    monto_cuotas = orden.monto_cuotas if orden.monto_cuotas is not None else 0

    p.drawString(100, y, "Tipo de Pago: {}".format(tipo_pago))
    p.drawString(100, y-15, "Monto de Cuotas: ${}".format(monto_cuotas))
    p.drawString(100, y-30, "Número de Cuotas: {}".format(orden.numero_cuotas))
    p.drawString(100, y-45, "Total (IVA incluido): ${}".format(orden.total))

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer

def generar_comprobante_online(request, numero_orden):
    """
    Genera un PDF en línea para descargar, que incluye detalles de la orden,
    tipo de pago y el total, y lo devuelve como una respuesta HTTP.
    """
    orden = get_object_or_404(VentaOnline, numero_orden=numero_orden)
    detalles = DetalleVentaOnline.objects.filter(orden_compra=orden)

    # Configuración de respuesta para descargar el PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="comprobante_orden_{}.pdf"'.format(orden.numero_orden)

    # Crear el contenido del PDF
    p = canvas.Canvas(response)

    # Datos de la empresa
    p.drawString(100, 800, "Empresa: Automotriz Urrutia")
    p.drawString(100, 785, "Número de Orden: {}".format(orden.numero_orden))

    # Datos del cliente autenticado o anónimo
    if orden.cliente:
        nombre = orden.cliente.user.first_name
        apellido = orden.cliente.user.last_name
        email = orden.cliente.user.username
    elif orden.cliente_anonimo:
        nombre = orden.cliente_anonimo.nombre
        apellido = orden.cliente_anonimo.apellido
        email = orden.cliente_anonimo.email
    else:
        nombre = "No disponible"
        apellido = "No disponible"
        email = "No disponible"

    # Imprimir los datos del cliente
    p.drawString(100, 770, "Cliente: {} {}".format(nombre, apellido))
    p.drawString(100, 755, "Correo Electrónico: {}".format(email))

    # Fecha y hora de la orden
    fecha_local = timezone.localtime(orden.fecha)
    p.drawString(100, 740, "Fecha y Hora: {}".format(fecha_local.strftime("%d/%m/%Y %H:%M")))
    p.drawString(100, 725, "Detalle:")

    # Detalle de productos o servicios
    y = 710
    for detalle in detalles:
        producto_o_servicio = detalle.producto if detalle.producto else detalle.servicio
        p.drawString(120, y, "{} - Cantidad: {} - Precio: ${}".format(producto_o_servicio.nombre, detalle.cantidad, detalle.precio))
        y -= 15

    # Tipo de pago y total
    tipo_pago_conversion = {
        'VD': 'Venta Débito',
        'VN': 'Venta Normal',
        'VC': 'Venta en Cuotas',
        'SI': '3 Cuotas sin Interés',
        'S2': '2 Cuotas sin Interés',
        'NC': 'N Cuotas sin Interés',
        'VP': 'Venta Prepago'
    }
    tipo_pago = tipo_pago_conversion.get(orden.tipo_pago, orden.tipo_pago)
    monto_cuotas = orden.monto_cuotas if orden.monto_cuotas is not None else 0

    p.drawString(100, y, "Tipo de Pago: {}".format(tipo_pago))
    p.drawString(100, y-15, "Monto de Cuotas: ${}".format(monto_cuotas))
    p.drawString(100, y-30, "Número de Cuotas: {}".format(orden.numero_cuotas))
    p.drawString(100, y-45, "Total (IVA incluido): ${}".format(orden.total))

    p.showPage()
    p.save()
    return response

def generar_comprobante(request, id_venta):
    """
    Genera un PDF de comprobante para una venta, que incluye el nombre del
    cliente, productos y/o servicios comprados, el total pagado y el vuelto.
    """
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="comprobante_venta_{id_venta}.pdf"'

    p = canvas.Canvas(response)
    venta = VentaManual.objects.get(id=id_venta)
    detalles = venta.detalleventamanual_set.all()

    y = 800  # Posición inicial en el eje Y para el texto

    # Cabecera de la empresa y detalles de venta
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y, "Empresa: Automotriz Urrutia")
    y -= 20

    p.drawString(100, y, f"Orden de Venta: {venta.id}")

    # Verificación de cliente anónimo
    if venta.cliente.user.username != "anonimo@gmail.com":
        p.drawString(100, y-20, f"Cliente: {venta.cliente.user.username}")
        y -= 40
    else:
        y -= 20

    p.drawString(100, y-20, f"Fecha: {venta.fecha_creacion.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(100, y-40, "Detalle:")

    # Detalles de productos y servicios
    y -= 80
    for detalle in detalles:
        if detalle.producto:
            p.drawString(120, y, f"Producto: {detalle.producto.nombre} - Cantidad: {detalle.cantidad} - Precio Unitario: ${detalle.producto.precio}")
            y -= 20
        if detalle.servicio:
            p.drawString(120, y, f"Servicio: {detalle.servicio.nombre} - Precio: ${detalle.servicio.precio}")
            y -= 20

    # Total, pago y vuelto
    p.drawString(100, y-20, f"Total (IVA incluido): ${venta.total}")
    p.drawString(100, y-40, f"Pagó: ${venta.pago_cliente}")
    p.drawString(100, y-60, f"Vuelto: ${venta.cambio}")

    p.showPage()
    p.save()
    return response

def top_cinco_productos_vendidos(anio, mes):
    """
    Retorna los cinco productos más vendidos en un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Producto.objects.filter(detalleventamanual__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

def top_cinco_servicios_vendidos(anio, mes):
    """
    Retorna los cinco servicios más vendidos en un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Servicio.objects.filter(detalleventamanual__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

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

def exportar_pdf(request):
    """
    Genera un reporte de ventas en PDF para el mes y año seleccionados. Incluye
    los cinco productos y servicios más vendidos con gráficos de torta y tablas.
    """
    anio = request.GET.get('anioParaPDF', str(datetime.now().year))
    mes = request.GET.get('mesParaPDF', str(datetime.now().month))

    top_cinco_productos = top_cinco_productos_vendidos(int(anio), int(mes))
    top_cinco_servicios = top_cinco_servicios_vendidos(int(anio), int(mes))

    # Calcular el total vendido de productos y servicios
    total_vendido_productos = sum([producto.total_vendido for producto in top_cinco_productos])
    total_vendido_servicios = sum([servicio.total_vendido for servicio in top_cinco_servicios])

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_ventas_{anio}_{mes}.pdf"'

    p = canvas.Canvas(response, pagesize=letter)
    nombre_mes = MES_ESPANOL.get(int(mes), "Mes desconocido")

    # Configuración inicial de la página y título del reporte
    y_position = 750
    p.drawString(100, y_position, f"Reporte de Ventas del mes {nombre_mes} del año {anio}")
    y_position -= 40

    # Sección de productos más vendidos
    if top_cinco_productos:
        p.drawString(100, y_position, "Top 5 Productos Más Vendidos")
        y_position -= 20

        datos_para_grafico_productos = {
            'labels': [producto.nombre for producto in top_cinco_productos],
            'values': [producto.total_vendido for producto in top_cinco_productos]
        }
        imagen_grafico_productos = generar_grafico_base64(datos_para_grafico_productos)
        imagen_grafico_productos = ImageReader(BytesIO(base64.b64decode(imagen_grafico_productos)))
        p.drawImage(imagen_grafico_productos, 100, y_position - 220, width=400, height=200)

        y_position -= 220 + 20

        # Tabla de productos vendidos
        data_productos = [['Producto', 'Cantidad', 'Porcentaje']]
        for producto in top_cinco_productos:
            porcentaje = (producto.total_vendido / total_vendido_productos * 100) if total_vendido_productos else 0
            data_productos.append([producto.nombre, producto.total_vendido, f"{porcentaje:.2f}%"])
        tabla_productos = Table(data_productos, colWidths=[200, 100, 100], hAlign='LEFT')
        tabla_productos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        tabla_productos.wrapOn(p, 400, 200)
        tabla_productos.drawOn(p, 100, y_position - 20 * len(data_productos) - 10)
        y_position -= 20 * len(data_productos) + 30
    else:
        p.drawString(100, y_position, "No se han registrado ventas de productos en el mes seleccionado.")
        y_position -= 30

    # Sección de servicios más vendidos en nueva página
    p.showPage()
    y_position = 750
    p.drawString(100, y_position, "Top 5 Servicios Más Vendidos")
    y_position -= 40

    if top_cinco_servicios:
        datos_para_grafico_servicios = {
            'labels': [servicio.nombre for servicio in top_cinco_servicios],
            'values': [servicio.total_vendido for servicio in top_cinco_servicios]
        }
        imagen_grafico_servicios = generar_grafico_base64(datos_para_grafico_servicios)
        imagen_grafico_servicios = ImageReader(BytesIO(base64.b64decode(imagen_grafico_servicios)))
        p.drawImage(imagen_grafico_servicios, 100, y_position - 220, width=400, height=200)
        y_position -= 220 + 20

        # Tabla de servicios vendidos
        data_servicios = [['Servicio', 'Cantidad', 'Porcentaje']]
        for servicio in top_cinco_servicios:
            porcentaje = (servicio.total_vendido / total_vendido_servicios * 100) if total_vendido_servicios else 0
            data_servicios.append([servicio.nombre, servicio.total_vendido, f"{porcentaje:.2f}%"])
        tabla_servicios = Table(data_servicios, colWidths=[200, 100, 100], hAlign='LEFT')
        tabla_servicios.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        tabla_servicios.wrapOn(p, 400, 200)
        tabla_servicios.drawOn(p, 100, y_position - 20 * len(data_servicios) - 10)
        y_position -= 20 * len(data_servicios) + 30
    else:
        p.drawString(100, y_position, "No se han registrado ventas de servicios en el mes seleccionado.")
        y_position -= 30

    # Guardar el PDF en la respuesta
    p.save()
    return response

def reportes_ventas_manuales(request):
    """
    Genera el contexto para la vista de reportes de ventas en la interfaz.
    Incluye el top 5 de productos y servicios en JSON para gráficos y mensajes
    si no hay datos.
    """
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month

    anio = int(request.GET.get('anio', anio_actual))
    mes = int(request.GET.get('mes', mes_actual))

    top_cinco_productos = top_cinco_productos_vendidos(anio, mes)
    top_cinco_servicios = top_cinco_servicios_vendidos(anio, mes)

    mensaje_productos = ""
    mensaje_servicios = ""

    if not top_cinco_productos:
        mensaje_productos = "No se han registrado ventas de productos en el mes seleccionado."

    if not top_cinco_servicios:
        mensaje_servicios = "No se han registrado ventas de servicios en el mes seleccionado."

    datos_productos = json.dumps({
        'labels': [producto.nombre for producto in top_cinco_productos],
        'data': [producto.total_vendido for producto in top_cinco_productos]
    }, cls=DjangoJSONEncoder) if top_cinco_productos else json.dumps({})

    datos_servicios = json.dumps({
        'labels': [servicio.nombre for servicio in top_cinco_servicios],
        'data': [servicio.total_vendido for servicio in top_cinco_servicios]
    }, cls=DjangoJSONEncoder) if top_cinco_servicios else json.dumps({})

    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    nombre_mes = meses.get(mes, "Mes desconocido")

    datos_grafico = {
        'labels': [producto.nombre for producto in top_cinco_productos],
        'values': [producto.total_vendido for producto in top_cinco_productos]
    }
    imagen_grafico = generar_grafico_base64(datos_grafico)

    contexto = {
        'datos_productos_json': datos_productos,
        'datos_servicios_json': datos_servicios,
        'mensaje_productos': mensaje_productos,
        'mensaje_servicios': mensaje_servicios,
        'rango_anios': range(2022, 2028),
        'rango_meses': range(1, 13),
        'anio_actual': anio_actual,
        'mes_actual': mes_actual,
        'anio_seleccionado': anio,
        'mes_seleccionado': mes,
        'nombre_mes': nombre_mes,
        'imagen_grafico': imagen_grafico,
        'top_cinco_productos': top_cinco_productos,
        'top_cinco_servicios': top_cinco_servicios,
    }

    return render(request, 'Transaccion/reportes_ventas_manuales.html', contexto)

