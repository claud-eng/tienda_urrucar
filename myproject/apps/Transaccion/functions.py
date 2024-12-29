import base64  # Importa el módulo base64 para codificación y decodificación de datos.
import json  # Importa el módulo json para manejar datos en formato JSON.
import matplotlib.pyplot as plt  # Importa pyplot de matplotlib para crear gráficos.
from datetime import datetime, timedelta  # Importa datetime y timedelta para manejar fechas y tiempos.
from django.conf import settings  # Importa la configuración de Django.
from django.contrib.staticfiles import finders  # Permite localizar archivos estáticos.
from django.core.mail import send_mail  # Importa la función para enviar correos electrónicos.
from django.core.serializers.json import DjangoJSONEncoder  # Importa el codificador JSON específico de Django.
from django.db.models import Sum  # Importa Sum para realizar sumas agregadas en consultas de modelos.
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse  # Importa clases de respuesta y redirección HTTP.
from django.shortcuts import get_object_or_404, redirect, render  # Importa funciones de atajos para renderizar y redireccionar vistas.
from django.utils import timezone  # Importa el módulo timezone para manejar zonas horarias.
from io import BytesIO  # Importa BytesIO para manejo de flujos de datos en memoria.
from reportlab.lib import colors  # Importa colores de ReportLab para crear gráficos y personalizar PDFs.
from reportlab.lib.pagesizes import A4, letter  # Importa tamaños de página 'A4' y 'letter' de ReportLab.
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

TIPO_PAGO_CONVERSION = {
    'VD': 'Venta Débito',
    'VN': 'Venta Normal',
    'VC': 'Venta en Cuotas',
    'SI': '3 Cuotas sin Interés',
    'S2': '2 Cuotas sin Interés',
    'NC': 'N Cuotas sin Interés',
    'VP': 'Venta Prepago'
}

# Función para generar un comprobante de pago en formato pdf
def generar_comprobante_pago_pdf(tipo_venta, id_venta=None, numero_orden=None, enviar_por_correo=False):
    if tipo_venta == 'manual':
        venta = get_object_or_404(VentaManual, id=id_venta)
        detalles = venta.detalleventamanual_set.all()
        filename = f"comprobante_pago_{venta.id}.pdf"
    elif tipo_venta == 'online':
        venta = get_object_or_404(VentaOnline, numero_orden=numero_orden)
        detalles = DetalleVentaOnline.objects.filter(orden_compra=venta)
        filename = f"comprobante_pago_{venta.numero_orden}.pdf"
    else:
        raise ValueError("Tipo de venta no reconocido")

    # Crear el PDF
    if enviar_por_correo:
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
    else:
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        p = canvas.Canvas(response, pagesize=A4)

    width, height = A4
    logo_path = finders.find('images/logo.png')

    # Agregar Logo
    p.drawImage(logo_path, 38, height - 146.5, width=150, height=150, preserveAspectRatio=True, mask='auto')

    # Título y cabecera
    p.setFont("Helvetica-Bold", 16)
    titulo = "Urrucar Automotriz"
    titulo_ancho = p.stringWidth(titulo, "Helvetica-Bold", 16)
    p.drawString((width - titulo_ancho) / 2, height - 80, titulo)

    p.setFont("Helvetica", 12)
    subtitulo = "Comprobante de Pago"
    subtitulo_ancho = p.stringWidth(subtitulo, "Helvetica", 12)
    p.drawString((width - subtitulo_ancho) / 2, height - 100, subtitulo)

    # Datos del cliente
    y = height - 150
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Orden de Venta:")
    p.setFont("Helvetica", 11)
    p.drawString(180, y, str(venta.numero_orden if tipo_venta == 'online' else venta.id))

    y -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Cliente:")
    if venta.cliente:
        nombre_cliente = venta.cliente.user.first_name
        apellido_cliente = venta.cliente.user.last_name
    else:
        nombre_cliente = venta.cliente_anonimo.nombre
        apellido_cliente = venta.cliente_anonimo.apellido

    nombre_completo = f"{nombre_cliente} {apellido_cliente}".strip()
    p.setFont("Helvetica", 11)
    p.drawString(180, y, nombre_completo)

    y -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Correo:")
    correo_cliente = venta.cliente.user.email if venta.cliente else venta.cliente_anonimo.email
    p.setFont("Helvetica", 11)
    p.drawString(180, y, correo_cliente)

    y -= 20
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Fecha y Hora:")
    fecha_venta = timezone.localtime(venta.fecha if tipo_venta == 'online' else venta.fecha_creacion)
    p.setFont("Helvetica", 11)
    p.drawString(180, y, fecha_venta.strftime("%d/%m/%Y %H:%M"))

    # Línea separadora
    p.line(50, y - 10, 550, y - 10)
    y -= 30

    # Detalles de productos o servicios
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Detalle:")
    y -= 30

    for detalle in detalles:
        producto_o_servicio = detalle.producto if detalle.producto else detalle.servicio
        if hasattr(detalle, 'precio'):  # DetalleVentaOnline
            precio_unitario = detalle.precio
        else:  # DetalleVentaManual
            precio_unitario = (
                detalle.producto.precio if detalle.producto
                else detalle.servicio.precio if detalle.servicio
                else 0
            )

        precio_formateado = format(int(precio_unitario), ',').replace(',', '.')
        p.drawString(70, y, f"{producto_o_servicio.nombre} - Cantidad: {detalle.cantidad} - Precio: ${precio_formateado}")
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 100
            p.drawString(100, y, "Detalle (continuación):")
            y -= 30

    # Línea separadora
    p.line(50, y, 550, y)
    y -= 30

    # Total y tipo de pago
    tipo_pago = (
        TIPO_PAGO_CONVERSION.get(venta.tipo_pago, venta.tipo_pago)
        if hasattr(venta, 'tipo_pago') else 'Venta Manual'
    )
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Tipo de Pago: {tipo_pago}")
    y -= 20
    p.drawString(50, y, f"Total (IVA incluido): ${format(int(venta.total), ',').replace(',', '.')}")
    y -= 20

    if tipo_venta == 'manual':
        p.drawString(50, y, f"Pagó: ${format(int(venta.pago_cliente), ',').replace(',', '.')}")
        y -= 20
        p.drawString(50, y, f"Vuelto: ${format(int(venta.cambio), ',').replace(',', '.')}")
    else:
        p.drawString(50, y, f"Número de Cuotas: {venta.numero_cuotas or 0}")
        y -= 20
        p.drawString(50, y, f"Monto de Cuotas: ${format(int(venta.monto_cuotas or 0), ',').replace(',', '.')}")

    p.showPage()
    p.save()

    if enviar_por_correo:
        buffer.seek(0)
        return buffer
    else:
        return response

# Función para poder descargar el comprobante de pago
def descargar_comprobante_pago(request, tipo_venta, identificador):
    if tipo_venta == 'manual':
        venta = get_object_or_404(VentaManual, id=identificador)
        response = generar_comprobante_pago_pdf(tipo_venta='manual', id_venta=venta.id, enviar_por_correo=False)
    elif tipo_venta == 'online':
        venta = get_object_or_404(VentaOnline, numero_orden=identificador)
        response = generar_comprobante_pago_pdf(tipo_venta='online', numero_orden=venta.numero_orden, enviar_por_correo=False)
    else:
        return HttpResponse("Tipo de venta no válido", status=400)
    
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

def reporte_ventas_manuales(request):
    """
    Genera el contexto para la vista de reportes de ventas manuales.
    Incluye el top 5 de productos y servicios en JSON para gráficos y mensajes
    si no hay datos. Permite filtrar por mes, trimestre, semestre o anual.
    """
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month

    # Obtener parámetros del GET (filtro dinámico)
    anio = int(request.GET.get('anio', anio_actual))
    tipo_filtro = request.GET.get('tipo_filtro', 'mes')  # 'mes', 'trimestre', 'semestre', 'anual'
    valor_filtro = int(request.GET.get('valor_filtro', mes_actual)) if tipo_filtro != 'anual' else None

    # Calcular rango de fechas según el filtro
    fecha_inicio, fecha_fin = calcular_rango_fechas(anio, tipo_filtro, valor_filtro)

    # Calcular el total de ventas (productos y servicios) en general
    total_productos = Producto.objects.filter(
        detalleventamanual__orden_compra__fecha_creacion__range=[fecha_inicio, fecha_fin]
    ).aggregate(total_vendido=Sum('detalleventamanual__cantidad'))['total_vendido'] or 0

    total_servicios = Servicio.objects.filter(
        detalleventamanual__orden_compra__fecha_creacion__range=[fecha_inicio, fecha_fin]
    ).aggregate(total_vendido=Sum('detalleventamanual__cantidad'))['total_vendido'] or 0

    # Obtener datos de ventas en ese rango de fechas
    top_cinco_productos = Producto.objects.filter(
        detalleventamanual__orden_compra__fecha_creacion__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

    top_cinco_servicios = Servicio.objects.filter(
        detalleventamanual__orden_compra__fecha_creacion__range=[fecha_inicio, fecha_fin]
    ).annotate(total_vendido=Sum('detalleventamanual__cantidad')).order_by('-total_vendido')[:5]

    # Mensajes si no hay productos o servicios vendidos
    mensaje_productos = ""
    mensaje_servicios = ""

    if not top_cinco_productos:
        filtro_texto = "año" if tipo_filtro == 'anual' else tipo_filtro
        mensaje_productos = f"No se han registrado ventas de productos en el {filtro_texto} seleccionado."

    if not top_cinco_servicios:
        filtro_texto = "año" if tipo_filtro == 'anual' else tipo_filtro
        mensaje_servicios = f"No se han registrado ventas de servicios en el {filtro_texto} seleccionado."

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

    # Trimestres, semestres y filtro anual
    trimestres = {1: '1er Trimestre', 2: '2do Trimestre', 3: '3er Trimestre', 4: '4to Trimestre'}
    semestres = {1: '1er Semestre', 2: '2do Semestre'}

    nombre_mes = meses.get(valor_filtro, "Anual") if tipo_filtro != 'anual' else "Anual"

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

    # Obtener el total general de ventas (productos y servicios)
    total_productos = Producto.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]
    ).aggregate(total_vendido=Sum('detalleventaonline__cantidad'))['total_vendido'] or 0

    total_servicios = Servicio.objects.filter(
        detalleventaonline__orden_compra__fecha__range=[fecha_inicio, fecha_fin]
    ).aggregate(total_vendido=Sum('detalleventaonline__cantidad'))['total_vendido'] or 0

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

    destinatario = "automotriz@urrucar.cl"
    
    # Enviar el correo
    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [destinatario],
        fail_silently=False
    )


