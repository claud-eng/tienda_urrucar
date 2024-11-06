import base64
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from django.db.models import Sum
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from .models import Carrito, DetalleOrdenCompra, DetalleOrdenVenta, OrdenDeCompra, OrdenDeVenta, Producto, Servicio

MES_ESPANOL = {

    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

def generar_comprobante_pdf_correo(orden):
    buffer = BytesIO()

    p = canvas.Canvas(buffer)

    # La lógica de dibujo es la misma que en generar_comprobante_online
    p.drawString(100, 800, "Empresa: Huellas Sanas S.A")
    p.drawString(100, 785, "Número de Orden: {}".format(orden.numero_orden))
    p.drawString(100, 770, "Cliente: {}".format(orden.cliente.user.username))

    fecha_local = timezone.localtime(orden.fecha)
    p.drawString(100, 755, "Fecha y Hora: {}".format(fecha_local.strftime("%d/%m/%Y %H:%M")))
    p.drawString(100, 740, "Detalle:")

    y = 725
    detalles = DetalleOrdenCompra.objects.filter(orden_compra=orden)
    for detalle in detalles:
        producto_o_servicio = detalle.producto if detalle.producto else detalle.servicio
        p.drawString(120, y, "{} - Cantidad: {} - Precio: ${}".format(producto_o_servicio.nombre, detalle.cantidad, detalle.precio))
        y -= 15

    # Conversión de tipo de pago
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
    orden = get_object_or_404(OrdenDeCompra, numero_orden=numero_orden)
    detalles = DetalleOrdenCompra.objects.filter(orden_compra=orden)

    # Crear un HttpResponse con los headers de PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="comprobante_orden_{}.pdf"'.format(orden.numero_orden)

    # Crear el PDF
    p = canvas.Canvas(response)

    p.drawString(100, 800, "Empresa: Huellas Sanas S.A")
    p.drawString(100, 785, "Número de Orden: {}".format(orden.numero_orden))
    p.drawString(100, 770, "Cliente: {}".format(orden.cliente.user.username))
    fecha_local = timezone.localtime(orden.fecha)
    p.drawString(100, 755, "Fecha y Hora: {}".format(fecha_local.strftime("%d/%m/%Y %H:%M")))
    p.drawString(100, 740, "Detalle:")

    y = 725
    for detalle in detalles:
        producto_o_servicio = detalle.producto if detalle.producto else detalle.servicio
        p.drawString(120, y, "{} - Cantidad: {} - Precio: ${}".format(producto_o_servicio.nombre, detalle.cantidad, detalle.precio))
        y -= 15

    # Conversión de tipo de pago
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

    # Manejo del monto de cuotas nulo
    monto_cuotas = orden.monto_cuotas if orden.monto_cuotas is not None else 0

    p.drawString(100, y, "Tipo de Pago: {}".format(tipo_pago))
    p.drawString(100, y-15, "Monto de Cuotas: ${}".format(monto_cuotas))
    p.drawString(100, y-30, "Número de Cuotas: {}".format(orden.numero_cuotas))
    p.drawString(100, y-45, "Total (IVA incluido): ${}".format(orden.total))

    p.showPage()
    p.save()
    return response

def generar_comprobante(request, id_venta):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="comprobante_venta_{id_venta}.pdf"'

    p = canvas.Canvas(response)
    venta = OrdenDeVenta.objects.get(id=id_venta)
    detalles = venta.detalleordenventa_set.all()

    y = 800  # Posición inicial en el eje Y para el texto

    # Añadir el nombre de la empresa
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y, "Empresa: Huellas Sanas S.A.")
    y -= 20  # Ajustar el eje Y para el siguiente texto

    # Detalles de la venta
    p.drawString(100, y, f"Orden de Venta: {venta.id}")

    # Verificar si el correo electrónico del cliente es diferente de anonimo@gmail.com
    if venta.cliente.user.username != "anonimo@gmail.com":
        p.drawString(100, y-20, f"Cliente: {venta.cliente.user.username}")
        y -= 40  # Ajustar el eje Y para el siguiente texto (con nombre del cliente)
    else:
        y -= 20  # Ajustar menos el eje Y si se omite el nombre del cliente

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

    p.drawString(100, y-20, f"Total (IVA incluido): ${venta.total}")
    p.drawString(100, y-40, f"Pagó: ${venta.pago_cliente}")
    p.drawString(100, y-60, f"Vuelto: ${venta.cambio}")

    p.showPage()
    p.save()
    return response

def top_cinco_productos_vendidos(anio, mes):
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Producto.objects.filter(detalleordenventa__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleordenventa__cantidad')).order_by('-total_vendido')[:5]

def top_cinco_servicios_vendidos(anio, mes):
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Servicio.objects.filter(detalleordenventa__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleordenventa__cantidad')).order_by('-total_vendido')[:5]

def generar_grafico_base64(datos):
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

    # La posición inicial en la página
    y_position = 750

    # Títulos de los gráficos
    p.drawString(100, y_position, f"Reporte de Ventas del mes {nombre_mes} del año {anio}")
    y_position -= 40

    # Dibujo del gráfico de productos
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
        # Después de dibujar el título "Top 5 Productos Más Vendidos"
        p.drawString(100, y_position, "Top 5 Productos Más Vendidos")
        y_position -= 40  # Tres líneas de espacio, asumiendo aproximadamente 20 puntos por línea

        # Ahora dibujamos el mensaje de "No se han registrado ventas..."
        p.drawString(100, y_position, "No se han registrado ventas de productos en el mes seleccionado.")
        y_position -= 30  # Ajustamos para la próxima línea o sección

    # Inmediatamente creamos una nueva página para los servicios
    p.showPage()
    y_position = 750
    p.drawString(100, y_position, "Top 5 Servicios Más Vendidos")
    y_position -= 40

    # Dibujo del gráfico de servicios en la segunda página
    if top_cinco_servicios:
        datos_para_grafico_servicios = {
            'labels': [servicio.nombre for servicio in top_cinco_servicios],
            'values': [servicio.total_vendido for servicio in top_cinco_servicios]
        }
        imagen_grafico_servicios = generar_grafico_base64(datos_para_grafico_servicios)
        imagen_grafico_servicios = ImageReader(BytesIO(base64.b64decode(imagen_grafico_servicios)))
        p.drawImage(imagen_grafico_servicios, 100, y_position - 220, width=400, height=200)
        y_position -= 220 + 20

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

    # Guardar el PDF en el objeto de respuesta
    p.save()
    return response