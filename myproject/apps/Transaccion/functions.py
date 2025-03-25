from .models import Carrito, DetalleVentaOnline, DetalleVentaManual, VentaOnline, VentaManual, Producto, Servicio  # Importa modelos de la aplicación actual.
from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

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
            if detalle.producto:
                precio_unitario = detalle.producto.precio
            elif detalle.servicio:
                # Si el precio del servicio es 0, usar el precio personalizado
                precio_unitario = detalle.servicio.precio if detalle.servicio.precio > 0 else venta.precio_personalizado or 0
            else:
                precio_unitario = 0

        precio_formateado = format(int(precio_unitario), ',').replace(',', '.')
        
        # Condición para productos de categoría "Vehículo"
        if detalle.producto and detalle.producto.categoria == "Vehículo":
            p.drawString(70, y, f"{producto_o_servicio.nombre} - Precio de Reserva: ${precio_formateado}")
        else:
            p.drawString(70, y, f"{producto_o_servicio.nombre} - Precio: ${precio_formateado}")
        
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
        p.drawString(50, y, f"Monto pagado hasta el día de hoy: ${format(int(venta.pago_cliente), ',').replace(',', '.')}")
        y -= 20
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

def envio_formulario_pago_administrador(datos_persona, datos_formulario, carrito_items):
    """
    Envía un correo electrónico al administrador con los datos del formulario dinámico,
    los datos de la persona, los productos adquiridos y los servicios contratados.
    """
    asunto = "Has recibido una nueva compra por Webpay"
    
    # Verifica si hay servicios en el carrito
    contiene_servicios = any(isinstance(item.item, Servicio) for item in carrito_items)

    # Agregar los datos de la persona al mensaje
    mensaje = "Datos del comprador:\n"
    mensaje += f"Nombre: {datos_persona.get('nombre', 'N/A')}\n"
    mensaje += f"Apellido: {datos_persona.get('apellido', 'N/A')}\n"
    mensaje += f"Correo: {datos_persona.get('email', 'N/A')}\n"
    mensaje += f"Teléfono: {datos_persona.get('numero_telefono', 'N/A')}\n"
    if contiene_servicios:
        mensaje += f"RUT: {datos_formulario.get('rut', 'N/A')}\n"  # Incluir RUT solo si hay servicios
    mensaje += "\n"

    # Agregar los productos adquiridos al mensaje
    mensaje += "Productos adquiridos:\n"
    productos_adquiridos = [
        f"- {item.item.nombre}" for item in carrito_items if isinstance(item.item, Producto)
    ]
    mensaje += "\n".join(productos_adquiridos) + "\n\n" if productos_adquiridos else "Ninguno\n\n"

    # Agregar los servicios contratados al mensaje
    mensaje += "Servicios contratados:\n"
    servicios_contratados = [
        f"- {item.item.nombre}" for item in carrito_items if isinstance(item.item, Servicio)
    ]
    mensaje += "\n".join(servicios_contratados) + "\n\n" if servicios_contratados else "Ninguno\n\n"

    # Incluir la información del formulario dinámica por servicio
    if servicios_contratados:
        mensaje += "Información específica por servicio contratado:\n\n"
        for item in carrito_items:
            if isinstance(item.item, Servicio):
                # Determinar campos relevantes según el servicio
                if item.item.nombre == "Revisión precompra":
                    campos_relevantes = {
                        'patente': "Patente",
                        'marca': "Marca",
                        'modelo': "Modelo",
                        'ano': "Año",
                        'direccion_inspeccion': "Dirección de Inspección",
                        'comuna': "Comuna",
                        'fecha_inspeccion': "Fecha de Inspección",
                    }
                elif item.item.nombre == "Solicitar revisión técnica":
                    campos_relevantes = {
                        'patente': "Patente",
                        'marca': "Marca",
                        'modelo': "Modelo",
                        'ano': "Año",
                        'direccion_retiro': "Dirección de Retiro",
                        'comuna': "Comuna",
                        'fecha_servicio': "Fecha del Servicio",
                    }
                elif item.item.nombre in ["Sacar tag", "Asesoría en realizar la transferencia de un vehículo"]:
                    campos_relevantes = {
                        'patente': "Patente",
                        'marca': "Marca",
                        'modelo': "Modelo",
                        'direccion': "Dirección",
                        'comuna': "Comuna",
                    }
                else:
                    campos_relevantes = {}

                # Agregar solo los campos relevantes al mensaje
                for campo, nombre_legible in campos_relevantes.items():
                    mensaje += f"{nombre_legible}: {datos_formulario.get(campo, 'N/A')}\n"
                mensaje += "\n"

    destinatario = "automotriz@urrucar.cl"
    
    # Enviar el correo
    send_mail(
        asunto,
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [destinatario],
        fail_silently=False
    )

# **Función para generar el PDF usando ReportLab**
def exportar_presupuesto_pdf(datos_presupuesto, items):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20)  # Reducir margen superior
    elementos = []
    estilos = getSampleStyleSheet()

    # Estilos personalizados
    estilo_titulo = ParagraphStyle(name="Titulo", parent=estilos["Title"], fontSize=14, alignment=TA_CENTER)
    estilo_justificado = ParagraphStyle(name="Justificado", parent=estilos["BodyText"], alignment=TA_JUSTIFY)
    estilo_datos = ParagraphStyle(name="Datos", parent=estilos["BodyText"], fontSize=10)
    estilo_etiqueta = ParagraphStyle(name="Etiqueta", fontSize=10, textColor="#149ddd")

    # **LOGO DE LA EMPRESA**
    logo_path = finders.find("images/logo.png")
    logo = Image(logo_path, width=150, height=150)  # Tamaño corregido

    # **Encabezado con Bordes Redondeados**
    encabezado_contenido = [
        ["Urrucar Automotriz"],
        ["Servicio Integral para Vehículos"],
        ["RUT: 77.602.093-1"],
        ["Tel: +569 61923925"],
        ["www.urrucar.cl"]
    ]

    tabla_encabezado = Table(encabezado_contenido, colWidths=[300])
    tabla_encabezado.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    # Contenedor del encabezado con caja redondeada y logo
    contenedor_encabezado = Table([
        [tabla_encabezado, logo]
    ], colWidths=[350, 150])

    contenedor_encabezado.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#ebebeb")),  # Gris claro #ebebeb
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', (0, 0), (-1, -1), 5)  # Bordes redondeados
    ]))

    elementos.append(contenedor_encabezado)
    elementos.append(Spacer(1, 12))

    # **Sección de Datos del Presupuesto con Bordes Redondeados y Ancho Completo**
    datos_presupuesto_contenido = [
        [Paragraph("<b>Presupuesto N°:</b> " + datos_presupuesto["numero_presupuesto"], estilo_titulo)]
    ]

    # **Usar el ancho total de la página**
    tabla_presupuesto_numero = Table(datos_presupuesto_contenido, colWidths=[470])
    tabla_presupuesto_numero.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5)
    ]))

    datos_cliente_contenido = [
        [Paragraph("<b>Cliente:</b>", estilo_etiqueta), Paragraph(datos_presupuesto['nombre_cliente'], estilo_datos),
        Paragraph("<b>RUT:</b>", estilo_etiqueta), Paragraph(datos_presupuesto['rut_cliente'], estilo_datos)],
        [Paragraph("<b>Teléfono:</b>", estilo_etiqueta), Paragraph(datos_presupuesto['telefono'], estilo_datos)],
        [Paragraph("<b>Fecha Presupuesto:</b>", estilo_etiqueta), 
        Paragraph(datetime.strptime(datos_presupuesto['fecha_presupuesto'], "%Y-%m-%d").strftime("%d/%m/%Y"), estilo_datos),
        Paragraph("<b>Validez hasta:</b>", estilo_etiqueta), 
        Paragraph(datetime.strptime(datos_presupuesto['fecha_validez'], "%Y-%m-%d").strftime("%d/%m/%Y"), estilo_datos)],
        [Paragraph("<b>Patente:</b>", estilo_etiqueta), Paragraph(datos_presupuesto['patente'], estilo_datos),
        Paragraph("<b>Vehículo:</b>", estilo_etiqueta), Paragraph(datos_presupuesto['vehiculo'], estilo_datos)],
        [Paragraph("<b>Año:</b>", estilo_etiqueta), Paragraph(datos_presupuesto['anio'], estilo_datos),
        Paragraph("<b>N° Chasis:</b>", estilo_etiqueta), Paragraph(datos_presupuesto['chasis'], estilo_datos)]
    ]

    tabla_datos_cliente = Table(datos_cliente_contenido, colWidths=[80, 180, 80, 180])
    tabla_datos_cliente.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))

    # Caja completa
    contenedor_datos_presupuesto = Table([[tabla_presupuesto_numero], [tabla_datos_cliente]], colWidths=[470])
    contenedor_datos_presupuesto.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#FFFFFF")),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('ROUNDEDCORNERS', (0, 0), (-1, -1), 5)
    ]))

    elementos.append(contenedor_datos_presupuesto)
    elementos.append(Spacer(1, 12))

    # **Observaciones**
    if datos_presupuesto["observaciones"]:
        elementos.append(Paragraph("<b>Observaciones:</b>", estilos["Normal"]))
        elementos.append(Paragraph(datos_presupuesto["observaciones"], estilo_justificado))
        elementos.append(Spacer(1, 12))

    # **Tabla de Ítems del Presupuesto**
    tabla_datos = [
        ["REFER.", "TIPO", "CONCEPTO", "CANT.", "PRECIO UNIT.", "DTO", "TOTAL"]
    ]

    total_presupuesto = 0

    # Definir estilo de párrafo para la columna "CONCEPTO"
    estilo_concepto = ParagraphStyle(
        name="Concepto",
        fontName="Helvetica",
        fontSize=10,
        leading=12,  # Espaciado entre líneas
        alignment=TA_LEFT,  # Alinear el texto a la izquierda
        wordWrap='CJK'  # Habilitar ajuste de texto automático
    )

    for item in items:
        referencia = item["referencia"]
        tipo = item["tipo"]
        concepto = Paragraph(item["concepto"], estilo_concepto)  # Convertir a Paragraph
        cantidad = item["cantidad"]
        precio_unitario = item["precio_unitario"]
        descuento = item["descuento"]
        total_item = (cantidad * precio_unitario) * ((100 - descuento) / 100)
        total_presupuesto += total_item

        # Reemplazar las comas por puntos en los montos
        def formatear_monto(monto):
            return f"${monto:,.0f}".replace(",", ".")

        tabla_datos.append([
            referencia, tipo, concepto, cantidad,
            formatear_monto(precio_unitario), f"{descuento}%", formatear_monto(total_item)
        ])

    tabla_items = Table(tabla_datos, colWidths=[50, 80, 160, 50, 80, 50, 80])
    tabla_items.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    
    elementos.append(tabla_items)
    elementos.append(Spacer(1, 12))

    # **Cálculo de Totales**
    subtotal = total_presupuesto
    iva = subtotal * 0.19
    total_final = subtotal + iva

    # **Tabla de Totales**
    totales = [
        ["Base Imponible", "IVA (19%)", "Total"],
        [formatear_monto(subtotal), formatear_monto(iva), formatear_monto(total_final)]
    ]
    tabla_totales = Table(totales, colWidths=[150, 150, 150])
    tabla_totales.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    # **Agregar la tabla de totales antes del total general**
    elementos.append(tabla_totales)
    elementos.append(Spacer(1, 12))

    # **TOTAL PRESUPUESTO en grande**
    elementos.append(Paragraph("TOTAL PRESUPUESTO: " + formatear_monto(total_final), estilo_titulo))

    # Generar PDF
    pdf.build(elementos)
    buffer.seek(0)
    return buffer

# **Función para generar el PDF usando ReportLab**
def exportar_informe_inspeccion_pdf(datos, imagenes, items_inspeccion, secciones_inspeccion):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20)
    estilos = getSampleStyleSheet()
    elementos = []

    estilo_titulo = ParagraphStyle(name="Titulo", parent=estilos["Title"], fontSize=14, alignment=TA_CENTER)
    estilo_dato = ParagraphStyle(name="Dato", fontSize=10)
    estilo_justificado = ParagraphStyle(name="Justificado", alignment=TA_JUSTIFY, fontSize=10)

    # Logo + Encabezado
    logo_path = finders.find("images/logo.png")
    logo = Image(logo_path, width=100, height=100)
    encabezado_contenido = [
        ["Urrucar Automotriz"],
        ["Servicio Integral para Vehículos"],
        ["RUT: 77.602.093-1"],
        ["Tel: +569 61923925"],
        ["www.urrucar.cl"]
    ]

    tabla_encabezado = Table(encabezado_contenido, colWidths=[300])
    tabla_encabezado.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    contenedor_encabezado = Table([
        [tabla_encabezado, logo]
    ], colWidths=[350, 150])

    contenedor_encabezado.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#ebebeb")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', (0, 0), (-1, -1), 5)
    ]))
    elementos.append(contenedor_encabezado)
    elementos.append(Spacer(1, 12))

    # **Título principal fuera de los cuadros**
    elementos.append(Paragraph("Informe de Inspección Precompra", estilo_titulo))
    elementos.append(Spacer(1, 12))

    tabla_inspector = Table([
        [Paragraph("<b>Fecha:</b>", estilo_dato), Paragraph(datetime.strptime(datos["fecha"], "%Y-%m-%dT%H:%M").strftime("%d/%m/%Y %H:%M"), estilo_dato),
         Paragraph("<b>Inspector:</b>", estilo_dato), Paragraph(datos["nombre_inspector"], estilo_dato)],
        [Paragraph("<b>Código Interno:</b>", estilo_dato), Paragraph(datos["codigo_interno"], estilo_dato), "", ""]
    ], colWidths=[80, 150, 80, 150])
    tabla_inspector.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10)
    ]))

    contenedor_inspector = Table([
        [Paragraph("<b>Datos de la Inspección</b>", estilo_titulo)],
        [tabla_inspector]
    ], colWidths=[470])
    contenedor_inspector.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#149ddd")),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    elementos.append(contenedor_inspector)
    elementos.append(Spacer(1, 12))

    # **Datos del Cliente**
    tabla_cliente = Table([
        [Paragraph("<b>Nombre:</b>", estilo_dato), Paragraph(datos["nombre_cliente"], estilo_dato),
         Paragraph("<b>RUT:</b>", estilo_dato), Paragraph(datos["rut_cliente"], estilo_dato)],
        [Paragraph("<b>Email:</b>", estilo_dato), Paragraph(datos["email"], estilo_dato),
         Paragraph("<b>Teléfono:</b>", estilo_dato), Paragraph(datos["telefono"], estilo_dato)]
    ], colWidths=[80, 150, 80, 150])
    tabla_cliente.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10)
    ]))

    contenedor_cliente = Table([
        [Paragraph("<b>Datos del Cliente</b>", estilo_titulo)],
        [tabla_cliente]
    ], colWidths=[470])
    contenedor_cliente.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#149ddd")),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    elementos.append(contenedor_cliente)
    elementos.append(Spacer(1, 12))

    # **Datos del Vehículo**
    tabla_vehiculo = Table([
        [Paragraph("<b>Patente:</b>", estilo_dato), Paragraph(datos["patente"], estilo_dato),
         Paragraph("<b>Año:</b>", estilo_dato), Paragraph(datos["anio"], estilo_dato)],
        [Paragraph("<b>Marca:</b>", estilo_dato), Paragraph(datos["marca"], estilo_dato),
         Paragraph("<b>Modelo:</b>", estilo_dato), Paragraph(datos["modelo"], estilo_dato)],
        [Paragraph("<b>Kilometraje:</b>", estilo_dato), Paragraph(f"{datos['kilometraje']} km", estilo_dato),
         Paragraph("<b>Color:</b>", estilo_dato), Paragraph(datos["color"], estilo_dato)]
    ], colWidths=[80, 150, 80, 150])
    tabla_vehiculo.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10)
    ]))

    contenedor_vehiculo = Table([
        [Paragraph("<b>Datos del Vehículo</b>", estilo_titulo)],
        [tabla_vehiculo]
    ], colWidths=[470])
    contenedor_vehiculo.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#149ddd")),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    elementos.append(contenedor_vehiculo)
    elementos.append(Spacer(1, 12))

    # **Conclusión de la Inspección**
    parrafo_conclusion = Paragraph(datos["conclusion"], estilo_justificado)

    contenedor_conclusion = Table([
        [Paragraph("<b>Conclusión de la Inspección</b>", estilo_titulo)],
        [parrafo_conclusion]
    ], colWidths=[470])
    contenedor_conclusion.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor("#149ddd")),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6)
    ]))
    elementos.append(contenedor_conclusion)

    # Si hay imágenes, agregarlas en bloques de 2 por fila
    if imagenes:
        bloque_fotografias = []
        bloque_fotografias.append(Spacer(1, 12))
        bloque_fotografias.append(Paragraph("<b>Fotografías</b>", estilo_titulo))
        bloque_fotografias.append(Spacer(1, 6))

        fila_imagenes = []
        max_ancho = 220  # Tamaño fijo
        max_alto = 150

        for idx, img in enumerate(imagenes):
            try:
                image_obj = Image(img, width=max_ancho, height=max_alto)

                fila_imagenes.append(image_obj)

                if len(fila_imagenes) == 2 or idx == len(imagenes) - 1:
                    # Rellenar si es impar
                    if len(fila_imagenes) == 1:
                        fila_imagenes.append(Spacer(1, max_alto))
                    tabla_fotos = Table([fila_imagenes], colWidths=[250, 250])
                    tabla_fotos.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 10)
                    ]))
                    bloque_fotografias.append(tabla_fotos)
                    fila_imagenes = []
            except Exception as e:
                print(f"Error al procesar imagen {idx + 1}: {e}")

        elementos.append(KeepTogether(bloque_fotografias))

    # **Informe Técnico**
    if items_inspeccion:
        elementos.append(Spacer(1, 12))
        elementos.append(Paragraph("<b>Informe Técnico</b>", estilo_titulo))
        elementos.append(Spacer(1, 6))

        seccion_actual = ""
        tabla_datos = [
            ["#", "Ítem", "Cumple", "No Aplica", "No Cumple", "Observaciones"]
        ]

        tabla_estilos = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (2, 1), (4, -1), 'CENTER'),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ]

        fila_idx = 1  # empieza después del encabezado

        for item in items_inspeccion:
            # Sección (por ejemplo: 1 de "1.3")
            seccion_num = item["numero"].split(".")[0]

            # Insertar título si cambia la sección
            if seccion_num != seccion_actual:
                seccion_actual = seccion_num
                titulo_idx = int(seccion_actual) - 1
                if 0 <= titulo_idx < len(secciones_inspeccion):
                    titulo = secciones_inspeccion[titulo_idx]["titulo"]
                    tabla_datos.append([Paragraph(f"<b>{titulo}</b>", estilo_dato)] + [""] * 5)
                    tabla_estilos.append(('SPAN', (0, fila_idx), (5, fila_idx)))
                    tabla_estilos.append(('BACKGROUND', (0, fila_idx), (5, fila_idx), colors.HexColor("#e0e0e0")))
                    fila_idx += 1

            cumple = "X" if item["estado"] == "Cumple" else ""
            no_aplica = "X" if item["estado"] == "No Aplica" else ""
            no_cumple = "X" if item["estado"] == "No Cumple" else ""

            descripcion = Paragraph(item["descripcion"], estilo_dato)
            observacion = Paragraph(item["observacion"], estilo_dato)

            tabla_datos.append([
                item["numero"],
                descripcion,
                cumple,
                no_aplica,
                no_cumple,
                observacion
            ])
            fila_idx += 1

        tabla_inspeccion = Table(tabla_datos, colWidths=[25, 210, 50, 50, 60, 100])
        tabla_inspeccion.setStyle(TableStyle(tabla_estilos))
        elementos.append(tabla_inspeccion)

        # INSPECCIONADO con subrayado justo debajo y texto centrado abajo
        estilo_inspeccionado = ParagraphStyle(
            name="Inspeccionado",
            alignment=TA_CENTER,
            fontSize=16,
            textColor=colors.HexColor("#66bb6a"),
            fontName="Helvetica-Bold",
        )

        estilo_footer = ParagraphStyle(
            name="Footer",
            alignment=TA_CENTER,
            fontSize=12,
            fontName="Helvetica-Bold"
        )

        # Tabla de 2 filas: INSPECCIONADO y Urrucar Automotriz
        tabla_inspeccionado = Table([
            [Paragraph("INSPECCIONADO", estilo_inspeccionado)],
            [Paragraph("Urrucar Automotriz", estilo_footer)]
        ], colWidths=[200])

        tabla_inspeccionado.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor("#149ddd")),  # solo en fila 0
        ]))

        # Añadir a los elementos
        elementos.append(Spacer(1, 16))
        elementos.append(tabla_inspeccionado)

    # Generar PDF
    pdf.build(elementos)
    buffer.seek(0)
    return buffer



