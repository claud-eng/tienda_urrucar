import os  # Importa el módulo 'os' para manejar variables de entorno.
import time  # Importa el módulo 'time' para operaciones relacionadas con el tiempo.
import uuid  # Importa el módulo 'uuid' para generar identificadores únicos.
from django.conf import settings  # Importa el módulo de configuración de Django.
from django.contrib import messages  # Importa el sistema de mensajes de Django para mostrar mensajes a los usuarios.
from django.core.mail import EmailMessage  # Importa la clase 'EmailMessage' para enviar correos electrónicos.
from django.http import HttpResponse  # Importa 'HttpResponse' para devolver respuestas HTTP.
from django.shortcuts import redirect, render  # Importa 'redirect' y 'render' para redirección y renderizado de plantillas.
from .functions import *  # Importa todas las funciones definidas en 'functions' del directorio actual.
from .models import Carrito, Cliente, DetalleVentaOnline, VentaOnline, Producto, Servicio  # Importa modelos necesarios para gestionar órdenes y carritos.
from .views import formato_precio  # Importa 'formato_precio' para formatear precios en vistas.
from transbank.common.integration_type import IntegrationType  # Importa 'IntegrationType' para configurar el entorno de integración de Webpay.
from transbank.common.options import WebpayOptions  # Importa 'WebpayOptions' para establecer opciones de configuración de Webpay.
from transbank.error.transbank_error import TransbankError  # Importa 'TransbankError' para manejar errores específicos de Transbank.
from transbank.webpay.webpay_plus.transaction import Transaction  # Importa 'Transaction' para realizar transacciones de Webpay Plus.

# Define las configuraciones de Webpay desde las variables de entorno
commerce_code = os.getenv('WEBPAY_COMMERCE_CODE')
api_key = os.getenv('WEBPAY_API_KEY')
webpay_options = WebpayOptions(commerce_code, api_key, IntegrationType.TEST)

def iniciar_transaccion(request):
    """
    Inicia una transacción de pago con Webpay para los elementos en el carrito
    del cliente. Genera un buy_order único y redirige a la URL de pago de Webpay
    si todo es correcto.
    """
    cliente = Cliente.objects.get(user=request.user)
    carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
    total = sum(item.obtener_precio_total() for item in carrito_items)

    # Verifica si el carrito está vacío y redirige si no hay productos
    if total == 0:
        messages.error(request, "Tu carrito está vacío.")
        return redirect('carrito')

    # Instancia la transacción con las opciones predefinidas
    tx = Transaction(webpay_options)

    # Genera un identificador único para el buy_order y ajusta su longitud
    timestamp = int(time.time())
    short_uuid = uuid.uuid4().hex[:10]
    buy_order = f"{timestamp}{short_uuid}"

    if len(buy_order) > 26:
        buy_order = buy_order[:26]

    session_id = request.session.session_key or 'session-unknown'
    amount = total
    return_url = request.build_absolute_uri('/transaccion/transaccion_finalizada/')

    # Intenta crear la transacción con Webpay
    try:
        response = tx.create(buy_order, session_id, amount, return_url)
        if 'url' in response and 'token' in response:
            # Redirige a la URL de Webpay para completar el pago
            return redirect(response['url'] + "?token_ws=" + response['token'])
        else:
            return HttpResponse("Error: la respuesta de Webpay no contiene URL o token")
    except TransbankError as e:
        print(e.message)
        return HttpResponse("Error al crear la transacción: " + str(e.message))

def transaccion_finalizada(request):
    """
    Completa la transacción de pago en Webpay, actualizando la orden y el estado
    del carrito según la respuesta del banco. Envía un correo de confirmación en
    caso de éxito.
    """
    token_ws = request.GET.get('token_ws')
    cliente = Cliente.objects.get(user=request.user)

    # Instancia la transacción con las opciones predefinidas
    tx = Transaction(webpay_options)

    try:
        # Confirma la transacción en Webpay usando el token
        response = tx.commit(token_ws)
        contexto = {}

        # Crea o recupera la orden de compra según el token_ws, evita duplicados
        orden, created = VentaOnline.objects.get_or_create(
            token_ws=token_ws,
            defaults={
                'cliente': cliente,
                'total': response.get('amount', 0),
                'estado': 'pendiente',
                'fecha': timezone.now(),
                'numero_orden': response.get('buy_order'),
                'tipo_pago': response.get('payment_type_code', None),
                'monto_cuotas': response.get('installments_amount', None),
                'numero_cuotas': response.get('installments_number', None)
            }
        )

        # Si la orden ya existe, muestra un mensaje de transacción procesada
        if not created:
            contexto['mensaje_error'] = "Esta transacción ya ha sido procesada."
            contexto['orden'] = orden
            contexto['orden'].total_formateado = formato_precio(orden.total)
            return render(request, 'Transaccion/retorno_webpay.html', contexto)

        detalles_compra = []
        transaccion_exitosa = False

        # Verifica si el estado de la transacción es autorizado
        if response.get('status') == 'AUTHORIZED':
            transaccion_exitosa = True
            carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
            stock_insuficiente = False

            # Verifica si hay suficiente stock para cada producto en el carrito
            for item in carrito_items:
                if isinstance(item.item, Producto) and item.item.cantidad_stock < item.cantidad:
                    stock_insuficiente = True
                    break

            if stock_insuficiente:
                orden.estado = 'rechazada'
                contexto['mensaje_error'] = "Stock insuficiente para uno o más productos."
                orden.save()
                return render(request, 'Transaccion/retorno_webpay.html', contexto)
            else:
                # Procesa cada ítem del carrito, actualizando su stock y detalles
                orden.estado = 'aprobada'
                for item in carrito_items:
                    detalle = {
                        'nombre': item.item.nombre,
                        'cantidad': item.cantidad,
                        'precio_unitario': formato_precio(item.item.precio),
                        'precio_total': formato_precio(item.obtener_precio_total())
                    }
                    detalles_compra.append(detalle)

                    if isinstance(item.item, Producto):
                        producto = item.item
                        producto.cantidad_stock -= item.cantidad
                        producto.save()

                        # Verifica si el producto pertenece a la categoría 'Vehículo'
                        if producto.categoria == "Vehículo":
                            DetalleVentaOnline.objects.create(
                                orden_compra=orden,
                                producto=producto,
                                precio=item.obtener_precio_total(),
                                cantidad=item.cantidad,
                                estado_reserva="En proceso"  # Establece automáticamente el estado de la reserva
                            )
                        else:
                            DetalleVentaOnline.objects.create(
                                orden_compra=orden,
                                producto=producto,
                                precio=item.obtener_precio_total(),
                                cantidad=item.cantidad
                            )
                    else:
                        DetalleVentaOnline.objects.create(
                            orden_compra=orden,
                            servicio=item.item,
                            precio=item.obtener_precio_total(),
                            cantidad=item.cantidad
                        )

                # Marca los ítems en el carrito como comprados
                carrito_items.update(carrito=0)

        else:
            # Marca la orden como rechazada si la transacción no es autorizada
            orden.estado = 'rechazada'
            contexto['mensaje_error'] = "Transacción rechazada por el banco"

        orden.save()

        # Configura el contexto para la plantilla de confirmación
        contexto['orden'] = orden
        contexto['orden'].total_formateado = formato_precio(orden.total)
        contexto['transaccion_exitosa'] = transaccion_exitosa
        contexto['detalles_compra'] = detalles_compra

        # Si la transacción es exitosa, genera y envía un comprobante por correo
        if transaccion_exitosa:
            buffer_pdf = generar_comprobante_pdf_correo(orden)

            email_subject = "Comprobante de Pago - Orden {}".format(orden.numero_orden)
            email_body = "Aquí está su comprobante de pago para la orden {}.".format(orden.numero_orden)
            email = EmailMessage(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [cliente.user.email]
            )

            email.attach('comprobante_orden_{}.pdf'.format(orden.numero_orden), buffer_pdf.getvalue(), 'application/pdf')
            email.send()

        return render(request, 'Transaccion/retorno_webpay.html', contexto)

    except TransbankError as e:
        # Verifica si el mensaje del error es específico
        if str(e.message) == "'token' can't be null or white space":
            contexto = {
                'mensaje_error': "Se ha anulado la compra. Por favor, inténtalo nuevamente."
            }
        else:
            contexto = {
                'mensaje_error': f"Error al procesar la transacción: {e.message}"
            }
        return render(request, 'Transaccion/retorno_webpay.html', contexto)