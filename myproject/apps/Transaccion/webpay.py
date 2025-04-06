import os  # Importa el módulo 'os' para manejar variables de entorno.
import time  # Importa el módulo 'time' para operaciones relacionadas con el tiempo.
import uuid  # Importa el módulo 'uuid' para generar identificadores únicos.
import logging # Importa 'logging' para crear registro de logs en un archivo.
from django.conf import settings  # Importa el módulo de configuración de Django.
from django.contrib import messages  # Importa el sistema de mensajes de Django para mostrar mensajes a los usuarios.
from django.core.mail import EmailMessage  # Importa la clase 'EmailMessage' para enviar correos electrónicos.
from django.core.mail import EmailMultiAlternatives  # Importa 'EmailMultiAlternatives' para enviar correos con formato HTML y texto plano.
from django.http import HttpResponse  # Importa 'HttpResponse' para devolver respuestas HTTP.
from django.shortcuts import redirect, render  # Importa 'redirect' y 'render' para redirección y renderizado de plantillas.
from django.template.loader import render_to_string  # Importa 'render_to_string' para renderizar plantillas a cadenas de texto.
from django.templatetags.static import static  # Importa 'static' para manejar rutas de archivos estáticos.
from django.utils import timezone # Importa el módulo timezone para manejar zonas horarias.
from django.utils.html import strip_tags  # Importa 'strip_tags' para eliminar etiquetas HTML de una cadena.
from django.utils.timezone import localtime  # Importa 'localtime' para trabajar con zonas horarias y convertir fechas a la zona local.
from transbank.common.integration_type import IntegrationType  # Importa 'IntegrationType' para configurar el entorno de integración de Webpay.
from transbank.common.options import WebpayOptions  # Importa 'WebpayOptions' para establecer opciones de configuración de Webpay.
from transbank.error.transbank_error import TransbankError  # Importa 'TransbankError' para manejar errores específicos de Transbank.
from transbank.webpay.webpay_plus.transaction import Transaction  # Importa 'Transaction' para realizar transacciones de Webpay Plus.
from .functions import *  # Importa todas las funciones definidas en 'functions' del directorio actual.
from .functions import TIPO_PAGO_CONVERSION  # Importa 'TIPO_PAGO_CONVERSION' desde functions, para convertir tipos de pago.
from .models import Carrito, Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, Producto, Servicio  # Importa modelos necesarios para gestionar órdenes y carritos.
from .views import formato_precio  # Importa 'formato_precio' para formatear precios en vistas.

# Configuración del logger
logger = logging.getLogger('webpay')

# Define las configuraciones de Webpay desde las variables de entorno
commerce_code = os.getenv('WEBPAY_COMMERCE_CODE')
api_key = os.getenv('WEBPAY_API_KEY')
webpay_options = WebpayOptions(commerce_code, api_key, IntegrationType.TEST)

def iniciar_transaccion(request):
    """
    Maneja transacciones de Webpay para clientes registrados y anónimos,
    actualizando los datos del formulario antes de iniciar la transacción.
    """
    cliente = None
    cliente_anonimo = None
    carrito_items = []

    if request.method == 'POST':
        # Captura los datos básicos del formulario
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        numero_telefono = request.POST.get('numero_telefono')

        # Captura datos adicionales del formulario dinámico
        datos_formulario_dinamico = {
            'rut': request.POST.get('rut'),
            'patente': request.POST.get('patente'),
            'marca': request.POST.get('marca'),
            'modelo': request.POST.get('modelo'),
            'ano': request.POST.get('ano'),
            'direccion_inspeccion': request.POST.get('direccion_inspeccion'),
            'direccion_retiro': request.POST.get('direccion_retiro'),
            'direccion': request.POST.get('direccion'),
            'comuna': request.POST.get('comuna'),
            'fecha_inspeccion': request.POST.get('fecha_inspeccion'),
            'fecha_servicio': request.POST.get('fecha_servicio'),
            'observaciones': request.POST.get('observaciones'),
        }

        # Obtiene la bandera desde la sesión
        contiene_servicios = request.session.get('contiene_servicios', False)
        print(f"Contiene servicios desde sesión: {contiene_servicios}")

        # Manejo de carrito según el tipo de usuario
        if request.user.is_authenticated:
            # Cliente autenticado
            try:
                cliente = Cliente.objects.get(user=request.user)
                carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
            except Cliente.DoesNotExist:
                messages.error(request, "Tu cuenta no está asociada a un cliente.")
                return redirect('carrito')
        else:
            # Cliente anónimo
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key

            cliente_anonimo, created = ClienteAnonimo.objects.get_or_create(session_key=session_key)

            # Actualiza los datos del cliente anónimo
            cliente_anonimo.nombre = nombre
            cliente_anonimo.apellido = apellido
            cliente_anonimo.email = email
            cliente_anonimo.numero_telefono = numero_telefono
            cliente_anonimo.save()

            carrito_items = Carrito.objects.filter(session_key=session_key, carrito=1)

        # Validar que el carrito no esté vacío
        if not carrito_items.exists():
            messages.error(request, "Tu carrito está vacío.")
            return redirect('carrito')

        # Validar los campos adicionales solo si contiene servicios
        if contiene_servicios:
            # Inicializa una lista vacía para los campos obligatorios
            campos_obligatorios = []

            # Inspecciona los ítems del carrito para identificar los servicios presentes
            for item in carrito_items:
                if item.item.nombre == "Revisión precompra":
                    campos_obligatorios += ['rut', 'patente', 'marca', 'modelo', 'ano', 'comuna', 'direccion_inspeccion', 'fecha_inspeccion']
                elif item.item.nombre == "Solicitar revisión técnica":
                    campos_obligatorios += ['rut', 'patente', 'marca', 'modelo', 'ano', 'comuna', 'direccion_retiro', 'fecha_servicio']
                elif item.item.nombre in ["Sacar tag", "Asesoría en realizar la transferencia de un vehículo"]:
                    campos_obligatorios += ['rut', 'patente', 'marca', 'modelo', 'direccion', 'comuna']

            # Validar los campos obligatorios
            for campo in campos_obligatorios:
                if not datos_formulario_dinamico.get(campo):
                    messages.error(request, "Por favor, completa todos los campos obligatorios del formulario.")
                    return redirect('carrito')
                
        # Validar que el carrito no esté vacío
        if not carrito_items.exists():
            messages.error(request, "Tu carrito está vacío.")
            return redirect('carrito')

        # Validación adicional: Verificar stock antes de redirigir a Webpay
        for item in carrito_items:
            if isinstance(item.item, Producto) and item.item.cantidad_stock < item.cantidad:
                messages.error(request, f"El producto {item.item.nombre} ya no tiene stock suficiente.")
                return redirect('carrito')

        # Guarda los datos adicionales en la sesión
        request.session['datos_formulario'] = datos_formulario_dinamico

        # Calcula el total del carrito
        total = sum(item.obtener_precio_total() for item in carrito_items)

        if total == 0:
            messages.error(request, "Tu carrito está vacío.")
            return redirect('carrito')

        # Instancia la transacción con las opciones predefinidas
        tx = Transaction(webpay_options)
        timestamp = int(time.time())
        short_uuid = uuid.uuid4().hex[:10]
        buy_order = f"{timestamp}{short_uuid}"[:26]
        session_id = request.session.session_key or 'session-unknown'
        amount = total
        return_url = request.build_absolute_uri('/transaccion/transaccion_finalizada/')

        try:
            # Crea la transacción con Webpay
            response = tx.create(buy_order, session_id, amount, return_url)
            if 'url' in response and 'token' in response:
                # Redirige a Webpay si la respuesta contiene URL y token
                return redirect(response['url'] + "?token_ws=" + response['token'])
            else:
                # Responde con un error si faltan la URL o el token
                return HttpResponse("Error: la respuesta de Webpay no contiene URL o token")
        except TransbankError as e:
            # Manejo de errores en la transacción
            return HttpResponse("Error al crear la transacción: " + str(e.message))

def transaccion_finalizada(request):
    """
    Completa la transacción de pago en Webpay, actualizando la orden y el estado
    del carrito según la respuesta del banco. Envía un correo de confirmación en
    caso de éxito. Además, genera un nuevo session_key para clientes anónimos.
    """

    # Capturar TBK_TOKEN y TBK_ORDEN_COMPRA si existen (indica transacción cancelada)
    tbk_token = request.GET.get('TBK_TOKEN')
    tbk_orden = request.GET.get('TBK_ORDEN_COMPRA')

    token_ws = request.GET.get('token_ws')
    cliente = None
    cliente_anonimo = None

    # Si TBK_TOKEN está presente, significa que la transacción fue cancelada
    if tbk_token:
        logger.warning(f"Transacción cancelada antes de completarse. Orden: {tbk_orden}, TBK_TOKEN: {tbk_token}")

    # Determina si el cliente es autenticado o anónimo
    if request.user.is_authenticated:
        cliente = Cliente.objects.get(user=request.user)
        carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
        logger.info(f"Cliente autenticado: {cliente.user.first_name} {cliente.user.last_name} {cliente.second_last_name} ({cliente.user.email})")
    else:
        session_key = request.session.session_key
        if not session_key:
            messages.error(request, "No hay información de sesión válida.")
            return redirect('carrito')

        cliente_anonimo = ClienteAnonimo.objects.filter(session_key=session_key).first()
        if not cliente_anonimo:
            messages.error(request, "No se encontró información del cliente anónimo.")
            return redirect('carrito')

        carrito_items = Carrito.objects.filter(session_key=session_key, carrito=1)
        logger.info(f"Cliente anónimo: {cliente_anonimo.nombre} {cliente_anonimo.apellido} ({cliente_anonimo.email}) con session_key: {session_key}")

    # Instancia la transacción con las opciones predefinidas
    tx = Transaction(webpay_options)
    try:
        if not token_ws:
            raise TransbankError("'token' can't be null or white space")  # Esto forzará que pase al except
        
        response = tx.commit(token_ws)
        logger.info(f"Respuesta de Webpay: {response}")

        contexto = {}

        # Crea o recupera la orden de compra
        orden, created = VentaOnline.objects.get_or_create(
            token_ws=token_ws,
            defaults={
                'cliente': cliente,
                'cliente_anonimo': cliente_anonimo,
                'total': response.get('amount', 0),
                'estado': 'pendiente',
                'fecha': timezone.now(),
                'numero_orden': response.get('buy_order'),
                'tipo_pago': response.get('payment_type_code', None),
                'monto_cuotas': response.get('installments_amount', None),
                'numero_cuotas': response.get('installments_number', None)
            }
        )

        if not created:
            # Si la orden ya existe, verificar si ya estaba procesada
            if orden.estado in ['aprobada', 'rechazada']:
                logger.warning(f"Orden ya existente con estado {orden.estado}. Se evita procesamiento duplicado. Orden: {orden.numero_orden}")
                contexto['mensaje_error'] = "Esta transacción ya ha sido procesada."
                contexto['orden'] = orden
                return render(request, 'Transaccion/retorno_webpay.html', contexto)
            
            # Si la orden existía pero aún no estaba procesada, actualizamos `token_ws` y `numero_orden`
            orden.token_ws = token_ws
            orden.numero_orden = response.get('buy_order')
            orden.save()

        detalles_compra = []
        transaccion_exitosa = response.get('status') == 'AUTHORIZED'

        # Verifica si la transacción es autorizada
        if transaccion_exitosa:
            stock_insuficiente = False
            for item in carrito_items:
                if isinstance(item.item, Producto) and item.item.cantidad_stock < item.cantidad:
                    stock_insuficiente = True
                    break

            if stock_insuficiente:
                orden.estado = 'rechazada'
                contexto['mensaje_error'] = "Lo sentimos, el producto que intentaste comprar ya no está disponible. La transacción ha sido anulada y el banco liberará el monto retenido pronto."
                orden.save()
                logger.error(f"Se ha creado un nuevo registro en la bdd con estado rechazada, Stock insuficiente encontrado. Orden: {orden.numero_orden}, Token WS: {token_ws}")

                # ANULAR la transacción en Webpay para que el dinero no quede retenido
                try:
                    response_refund = tx.refund(token_ws, orden.total)
                    logger.info(f"Se realizó una anulación de la transacción para {token_ws}")
                except TransbankError as e:
                    logger.error(f"Error al anular la transacción: {e.message}")

                return render(request, 'Transaccion/retorno_webpay.html', contexto)

            # Procesar ítems del carrito
            orden.estado = 'aprobada'

            # Obtener los datos del comprador
            datos_persona = {
                'nombre': cliente.user.first_name if cliente else cliente_anonimo.nombre,
                'apellido': cliente.user.last_name if cliente else cliente_anonimo.apellido,
                'email': cliente.user.email if cliente else cliente_anonimo.email,
                'numero_telefono': cliente.numero_telefono if cliente else cliente_anonimo.numero_telefono,
            }

            # Capturar datos del formulario dinámico
            datos_formulario = request.session.pop('datos_formulario', {})

            # Enviar correo al administrador
            envio_formulario_pago_administrador(datos_persona, datos_formulario, carrito_items)

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

                    if producto.categoria == "Vehículo":
                        DetalleVentaOnline.objects.create(
                            orden_compra=orden,
                            producto=producto,
                            precio=item.obtener_precio_total(),
                            cantidad=item.cantidad,
                            estado_reserva="En proceso"
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
                        cantidad=item.cantidad,
                        marca_vehiculo=datos_formulario.get('marca'),
                        modelo_vehiculo=datos_formulario.get('modelo'),
                        patente_vehiculo=datos_formulario.get('patente'),
                    )

            carrito_items.update(carrito=0)
            logger.info("Ítems del carrito procesados y actualizados.")

        else:
            # Transacción rechazada
            orden.estado = 'rechazada'
            orden.save()
            contexto['mensaje_error'] = "Transacción rechazada por el banco."
            logger.error(f"Se ha creado un nuevo registro en la bdd con estado rechazada, Transacción rechazada por el banco. Orden: {orden.numero_orden}, Token WS: {token_ws}")

            # Generar un nuevo session_key y crear un nuevo cliente anónimo
            if not request.user.is_authenticated:
                old_session_key = request.session.session_key
                request.session.flush()
                request.session.create()
                new_session_key = request.session.session_key

                logger.warning(f"Session key reiniciado dado que la compra fue rechazada: {old_session_key} -> {new_session_key}")

                nuevo_cliente_anonimo = ClienteAnonimo.objects.create(
                    nombre="Anónimo",
                    apellido="",
                    email=f"anonimo_{new_session_key}@example.com",
                    numero_telefono="",
                    session_key=new_session_key
                )
                logger.info(f"Se ha creado un nuevo cliente anónimo: {nuevo_cliente_anonimo.email} con session_key: {new_session_key}")

            return render(request, 'Transaccion/retorno_webpay.html', contexto)

        orden.save()

        # Configuración del contexto
        orden.total_formateado = formato_precio(orden.total)
        contexto.update({
            'orden': orden,
            'transaccion_exitosa': transaccion_exitosa,
            'detalles_compra': detalles_compra
        })

        if transaccion_exitosa:
            if isinstance(orden, VentaOnline):
                buffer_pdf = generar_comprobante_pago_pdf(tipo_venta='online', numero_orden=orden.numero_orden)
            elif isinstance(orden, VentaManual):
                buffer_pdf = generar_comprobante_pago_pdf(tipo_venta='manual', id_venta=orden.id)
            else:
                raise ValueError("Tipo de venta no reconocido")
            
            logger.error(f"Se ha creado un nuevo registro en la bdd con estado aprobada. Orden: {orden.numero_orden}, Token WS: {token_ws}")

            # URL del logo
            logo_url = request.build_absolute_uri(static('images/logo.png'))
            
            # Renderizar plantilla HTML
            email_html = render_to_string('Transaccion/comprobante_pago.html', {
                'cliente_nombre': cliente.user.first_name if cliente else cliente_anonimo.nombre,
                'numero_orden': orden.numero_orden,
                'fecha_compra': localtime(orden.fecha).strftime("%d/%m/%Y %H:%M"),
                'total': formato_precio(orden.total),
                'tipo_pago': TIPO_PAGO_CONVERSION.get(orden.tipo_pago, orden.tipo_pago),
                'logo_url': logo_url,
            })

            # Convertir HTML a texto plano
            email_texto = strip_tags(email_html)
            
            email_subject = f"Comprobante de Pago - Orden {orden.numero_orden}"
            
            email = EmailMultiAlternatives(
                email_subject,
                email_texto,
                settings.DEFAULT_FROM_EMAIL,
                [cliente.user.email] if cliente else [cliente_anonimo.email]
            )
            
            email.attach_alternative(email_html, "text/html")
            email.attach(f'comprobante_pago_{orden.numero_orden}.pdf', buffer_pdf.getvalue(), 'application/pdf')
            email.send()
            logger.info("Comprobante enviado por correo.")

            # Generar un nuevo session_key y crear un nuevo cliente anónimo
            if not request.user.is_authenticated:
                old_session_key = request.session.session_key
                request.session.flush()
                request.session.create()
                new_session_key = request.session.session_key

                logger.warning(f"Session key reiniciado dado que la compra fue exitósa: {old_session_key} -> {new_session_key}")

                # Crear un nuevo cliente anónimo con valores predeterminados
                nuevo_cliente_anonimo = ClienteAnonimo.objects.create(
                    nombre="Anónimo",
                    apellido="",
                    email=f"anonimo_{new_session_key}@example.com",
                    numero_telefono="",
                    session_key=new_session_key
                )
                logger.info(f"Se ha creado un nuevo cliente anónimo: {nuevo_cliente_anonimo.email} con session_key: {new_session_key}")

        return render(request, 'Transaccion/retorno_webpay.html', contexto)

    except TransbankError as e:
        # Manejo de error en la transacción
        logger.error(f"Error en la transacción: {e.message}")

        # Intentar encontrar la orden original por `TBK_ORDEN_COMPRA`
        orden = VentaOnline.objects.filter(numero_orden=tbk_orden).first()

        if orden:
            # Si ya existe, actualizar su estado a "anulada" y guardar TBK_TOKEN
            orden.estado = 'anulada'
            orden.token_ws = None
            orden.tbk_token = tbk_token
            orden.tipo_pago = None
            orden.monto_cuotas = None
            orden.numero_cuotas = None
            orden.save()
            logger.warning(f"La orden {orden.numero_orden} ha sido marcada como anulada. TBK_TOKEN: {tbk_token}")
        else:
            # Si no existe en la BD, crear una nueva orden con la información correcta
            nueva_orden = VentaOnline.objects.create(
                cliente=cliente,
                cliente_anonimo=cliente_anonimo,
                total=0,
                estado='anulada',
                fecha=timezone.now(),
                numero_orden=tbk_orden,
                token_ws=None,
                tbk_token=tbk_token,
                tipo_pago=None,
                monto_cuotas=None,
                numero_cuotas=None
            )

            logger.warning(f"Se ha creado un nuevo registro en la bdd con estado anulada. Orden: {nueva_orden.numero_orden}, TBK_TOKEN: {tbk_token}")

        # Reiniciar sesión y crear un nuevo cliente anónimo
        if not request.user.is_authenticated:
            old_session_key = request.session.session_key
            request.session.flush()
            request.session.create()
            new_session_key = request.session.session_key

            logger.warning(f"Session key reiniciado dado que la compra fue anulada: {old_session_key} -> {new_session_key}")

            nuevo_cliente_anonimo = ClienteAnonimo.objects.create(
                nombre="Anónimo",
                apellido="",
                email=f"anonimo_{new_session_key}@example.com",
                numero_telefono="",
                session_key=new_session_key
            )
            logger.info(f"Se ha creado un nuevo cliente anónimo: {nuevo_cliente_anonimo.email} con session_key: {new_session_key}")

        # Modificar el mensaje de error solo si el token es nulo
        if "'token' can't be null or white space" in e.message:
            contexto = {'mensaje_error': "La compra ha sido anulada por el usuario."}
        else:
            contexto = {'mensaje_error': f"Error al procesar la transacción: {e.message}"}

        return render(request, 'Transaccion/retorno_webpay.html', contexto)

