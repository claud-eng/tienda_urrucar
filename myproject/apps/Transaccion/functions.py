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
from django.core.mail import send_mail
from django.conf import settings

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
    Calcula el rango de fechas basado en el tipo de filtro (mes, trimestre o semestre).
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
    return fecha_inicio, fecha_fin

def top_cinco_productos_manuales(anio, mes):
    """
    Retorna los cinco productos más vendidos en un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Producto.objects.filter(detalleventamanual__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

def top_cinco_servicios_manuales(anio, mes):
    """
    Retorna los cinco servicios más vendidos en un mes específico.
    """
    fecha_inicio = datetime(anio, mes, 1)
    fecha_fin = datetime(anio, mes + 1, 1) if mes < 12 else datetime(anio + 1, 1, 1)
    return Servicio.objects.filter(detalleventamanual__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

def reporte_ventas_manuales(request):
    """
    Genera el contexto para la vista de reportes de ventas en la interfaz.
    Incluye el top 5 de productos y servicios en JSON para gráficos y mensajes
    si no hay datos. Permite filtrar por mes, trimestre y semestre.
    """
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month

    # Obtener parámetros del GET (filtro dinámico)
    anio = int(request.GET.get('anio', anio_actual))
    tipo_filtro = request.GET.get('tipo_filtro', 'mes')  # 'mes', 'trimestre', 'semestre'
    valor_filtro = int(request.GET.get('valor_filtro', mes_actual))

    # Calcular rango de fechas según el filtro
    fecha_inicio, fecha_fin = calcular_rango_fechas(anio, tipo_filtro, valor_filtro)

    # Obtener datos de ventas en ese rango de fechas
    top_cinco_productos = Producto.objects.filter(
        detalleventamanual__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

    top_cinco_servicios = Servicio.objects.filter(
        detalleventamanual__orden_venta__fecha_creacion__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

    # Mensajes si no hay productos o servicios vendidos
    mensaje_productos = ""
    mensaje_servicios = ""

    if not top_cinco_productos:
        mensaje_productos = f"No se han registrado ventas de productos en el {tipo_filtro} seleccionado."

    if not top_cinco_servicios:
        mensaje_servicios = f"No se han registrado ventas de servicios en el {tipo_filtro} seleccionado."

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

    # Trimestres y semestres para mostrar en el filtro
    trimestres = {1: '1er Trimestre', 2: '2do Trimestre', 3: '3er Trimestre', 4: '4to Trimestre'}
    semestres = {1: '1er Semestre', 2: '2do Semestre'}

    nombre_mes = meses.get(valor_filtro, "Mes desconocido")

    datos_grafico = {
        'labels': [producto.nombre for producto in top_cinco_productos],
        'values': [producto.total_vendido for producto in top_cinco_productos]
    }
    imagen_grafico = generar_grafico_base64(datos_grafico)

    # Contexto para la plantilla
    contexto = {
        'datos_productos_json': datos_productos,
        'datos_servicios_json': datos_servicios,
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

def reporte_ventas_online(request):
    """
    Genera el contexto para el reporte de ventas online.
    Permite filtrar por mes, trimestre o semestre.
    """
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month

    # Obtener parámetros del GET (filtro dinámico)
    anio = int(request.GET.get('anio', anio_actual))
    tipo_filtro = request.GET.get('tipo_filtro', 'mes')  # 'mes', 'trimestre', 'semestre'
    valor_filtro = int(request.GET.get('valor_filtro', mes_actual))

    # Calcular rango de fechas según el filtro
    fecha_inicio, fecha_fin = calcular_rango_fechas(anio, tipo_filtro, valor_filtro)

    # Obtener datos de ventas online dentro del rango
    top_cinco_productos = Producto.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventaonline__cantidad')).order_by('-total_vendido')[:5]

    top_cinco_servicios = Servicio.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventaonline__cantidad')).order_by('-total_vendido')[:5]

    # Mensajes si no hay productos o servicios vendidos
    mensaje_productos = ""
    mensaje_servicios = ""

    if not top_cinco_productos:
        mensaje_productos = f"No se han registrado ventas de productos online en el {tipo_filtro} seleccionado."

    if not top_cinco_servicios:
        mensaje_servicios = f"No se han registrado ventas de servicios online en el {tipo_filtro} seleccionado."

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

    # Trimestres y semestres para mostrar en el filtro
    trimestres = {1: '1er Trimestre', 2: '2do Trimestre', 3: '3er Trimestre', 4: '4to Trimestre'}
    semestres = {1: '1er Semestre', 2: '2do Semestre'}

    nombre_mes = meses.get(valor_filtro, "Mes desconocido")

    datos_grafico = {
        'labels': [producto.nombre for producto in top_cinco_productos],
        'values': [producto.total_vendido for producto in top_cinco_productos]
    }
    imagen_grafico = generar_grafico_base64(datos_grafico)

    # Contexto para la plantilla
    contexto = {
        'datos_productos_json': datos_productos,
        'datos_servicios_json': datos_servicios,
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

def envio_formulario_pago_administrador(datos_persona, datos_formulario, carrito_items):
    """
    Envía un correo electrónico al administrador con los datos del formulario dinámico,
    los datos de la persona, los productos adquiridos y los servicios contratados.
    """
    asunto = "Has recibido una nueva compra por Webpay"
    
    # Agregar los datos de la persona al mensaje
    mensaje = "Datos del comprador:\n"
    mensaje += f"Nombre: {datos_persona.get('nombre', 'N/A')}\n"
    mensaje += f"Apellido: {datos_persona.get('apellido', 'N/A')}\n"
    mensaje += f"Correo: {datos_persona.get('email', 'N/A')}\n"
    mensaje += f"Teléfono: {datos_persona.get('numero_telefono', 'N/A')}\n\n"

    # Agregar los productos adquiridos al mensaje
    mensaje += "Productos adquiridos:\n"
    productos_adquiridos = [
        f"- {item.item.nombre}" for item in carrito_items if isinstance(item.item, Producto)
    ]
    if productos_adquiridos:
        mensaje += "\n".join(productos_adquiridos) + "\n\n"
    else:
        mensaje += "Ninguno\n\n"

    # Agregar los servicios contratados al mensaje
    mensaje += "Servicios contratados:\n"
    servicios_contratados = [
        f"- {item.item.nombre}" for item in carrito_items if isinstance(item.item, Servicio)
    ]
    if servicios_contratados:
        mensaje += "\n".join(servicios_contratados) + "\n\n"
    else:
        mensaje += "Ninguno\n\n"

    # Incluir la información del formulario dinámico solo si hay servicios contratados
    if servicios_contratados:
        mensaje += "Información del vehículo al contratar uno o más servicios:\n"
        
        # Mapeo de campos a nombres legibles
        mapeo_campos = {
            'nombre_vehiculo': "Nombre del Vehículo",
            'marca': "Marca",
            'ano': "Año",
            'retiro_domicilio': "Retiro a Domicilio",
            'direccion': "Dirección",
            'descripcion_vehiculo': "Descripción del Vehículo",
        }

        for campo, valor in datos_formulario.items():
            nombre_legible = mapeo_campos.get(campo, campo)
            mensaje += f"{nombre_legible}: {valor if valor else 'N/A'}\n"

    destinatario = "czamorano@claudev.cl"
    
    # Enviar el correo
    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [destinatario],
        fail_silently=False
    )


