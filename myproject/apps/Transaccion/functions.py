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



