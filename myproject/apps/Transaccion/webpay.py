import os  # Importa el módulo 'os' para manejar variables de entorno.
import time  # Importa el módulo 'time' para operaciones relacionadas con el tiempo.
import uuid  # Importa el módulo 'uuid' para generar identificadores únicos.
from django.conf import settings  # Importa el módulo de configuración de Django.
from django.contrib import messages  # Importa el sistema de mensajes de Django para mostrar mensajes a los usuarios.
from django.core.mail import EmailMessage  # Importa la clase 'EmailMessage' para enviar correos electrónicos.
from django.http import HttpResponse  # Importa 'HttpResponse' para devolver respuestas HTTP.
from django.shortcuts import redirect, render  # Importa 'redirect' y 'render' para redirección y renderizado de plantillas.
from .functions import *  # Importa todas las funciones definidas en 'functions' del directorio actual.
from .models import Carrito, Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, Producto, Servicio  # Importa modelos necesarios para gestionar órdenes y carritos.
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
    Maneja transacciones de Webpay para clientes registrados y anónimos,
    actualizando los datos del formulario antes de iniciar la transacción.
    """
    cliente = None
    cliente_anonimo = None

    if request.method == 'POST':
        # Captura los datos básicos del formulario
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        email = request.POST.get('email')
        numero_telefono = request.POST.get('numero_telefono')

        # Captura datos adicionales del formulario dinámico
        datos_formulario_dinamico = {
            'nombre_vehiculo': request.POST.get('nombre_vehiculo'),
            'marca': request.POST.get('marca'),
            'ano': request.POST.get('ano'),
            'retiro_domicilio': request.POST.get('retiro_domicilio'),
            'direccion': request.POST.get('direccion'),
            'descripcion_vehiculo': request.POST.get('descripcion_vehiculo'),
        }

        # Obtiene la bandera desde la sesión
        contiene_servicios = request.session.get('contiene_servicios', False)
        print(f"Contiene servicios desde sesión: {contiene_servicios}")

        # Validar los campos adicionales solo si el carrito contiene servicios
        if contiene_servicios:
            campos_obligatorios = ['nombre_vehiculo', 'marca', 'ano']
            if datos_formulario_dinamico.get('retiro_domicilio') == 'Si':
                campos_obligatorios.append('direccion')
            for campo in campos_obligatorios:
                if not datos_formulario_dinamico.get(campo):
                    messages.error(request, "Por favor, completa todos los campos obligatorios del formulario.")
                    return redirect('carrito')

        # Guarda los datos adicionales en la sesión
        request.session['datos_formulario'] = datos_formulario_dinamico

        if request.user.is_authenticated:
            # Cliente autenticado
            cliente = Cliente.objects.get(user=request.user)
            carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
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
    token_ws = request.GET.get('token_ws')
    cliente = None
    cliente_anonimo = None

    # Determina si el cliente es autenticado o anónimo
    if request.user.is_authenticated:
        cliente = Cliente.objects.get(user=request.user)
        carrito_items = Carrito.objects.filter(cliente=cliente, carrito=1)
        print(f"Cliente autenticado: {cliente.user.email}")
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
        print(f"Cliente anónimo: {cliente_anonimo.email} con session_key: {session_key}")

    # Instancia la transacción con las opciones predefinidas
    tx = Transaction(webpay_options)
    try:
        response = tx.commit(token_ws)
        print(f"Respuesta de Webpay: {response}")

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
            print("Orden ya existente. Se evita procesamiento duplicado.")
            contexto['mensaje_error'] = "Esta transacción ya ha sido procesada."
            contexto['orden'] = orden
            return render(request, 'Transaccion/retorno_webpay.html', contexto)

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
                contexto['mensaje_error'] = "Stock insuficiente para uno o más productos."
                orden.save()
                print("Stock insuficiente encontrado.")
                return render(request, 'Transaccion/retorno_webpay.html', contexto)

            # Procesar ítems del carrito
            orden.estado = 'aprobada'

            # Obtener los datos del comprador
            datos_persona = {
                'nombre': cliente.nombre if cliente else cliente_anonimo.nombre,
                'apellido': cliente.apellido if cliente else cliente_anonimo.apellido,
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
                        cantidad=item.cantidad
                    )

            carrito_items.update(carrito=0)
            print("Ítems del carrito procesados y actualizados.")

        else:
            # Transacción rechazada
            orden.estado = 'rechazada'
            orden.save()
            contexto['mensaje_error'] = "Transacción rechazada por el banco."
            print("Transacción rechazada por el banco.")

            # Generar un nuevo session_key y crear un nuevo cliente anónimo
            if not request.user.is_authenticated:
                old_session_key = request.session.session_key
                request.session.flush()
                request.session.create()
                new_session_key = request.session.session_key

                print(f"Session key reiniciado (rechazada): {old_session_key} -> {new_session_key}")

                nuevo_cliente_anonimo = ClienteAnonimo.objects.create(
                    nombre="Anónimo",
                    apellido="",
                    email=f"anonimo_{new_session_key}@example.com",
                    numero_telefono="",
                    session_key=new_session_key
                )
                print(f"Nuevo cliente anónimo creado (rechazada): {nuevo_cliente_anonimo.email} con session_key: {new_session_key}")

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
            buffer_pdf = generar_comprobante_pdf_correo(orden)
            email_subject = f"Comprobante de Pago - Orden {orden.numero_orden}"
            email_body = f"Aquí está su comprobante de pago para la orden {orden.numero_orden}."
            email = EmailMessage(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [cliente.user.email] if cliente else [cliente_anonimo.email]
            )
            email.attach(f'comprobante_orden_{orden.numero_orden}.pdf', buffer_pdf.getvalue(), 'application/pdf')
            email.send()
            print("Comprobante enviado por correo.")

            # Generar un nuevo session_key y crear un nuevo cliente anónimo
            if not request.user.is_authenticated:
                old_session_key = request.session.session_key
                request.session.flush()
                request.session.create()
                new_session_key = request.session.session_key

                print(f"Session key reiniciado: {old_session_key} -> {new_session_key}")

                # Crear un nuevo cliente anónimo con valores predeterminados
                nuevo_cliente_anonimo = ClienteAnonimo.objects.create(
                    nombre="Anónimo",
                    apellido="",
                    email=f"anonimo_{new_session_key}@example.com",
                    numero_telefono="",
                    session_key=new_session_key
                )
                print(f"Nuevo cliente anónimo creado: {nuevo_cliente_anonimo.email} con session_key: {new_session_key}")

        return render(request, 'Transaccion/retorno_webpay.html', contexto)

    except TransbankError as e:
        # Manejo de error en la transacción
        print(f"Error en la transacción: {e.message}")

        # Siempre crear una nueva orden anulada con un identificador único
        nueva_orden = VentaOnline.objects.create(
            cliente=cliente,
            cliente_anonimo=cliente_anonimo,
            total=0,
            estado='anulada',
            fecha=timezone.now(),
            numero_orden='error_' + str(timezone.now().timestamp()).replace('.', ''),  # Identificador único
            tipo_pago=None,
            monto_cuotas=None,
            numero_cuotas=None,
            token_ws=f"error_{timezone.now().timestamp()}"  # Genera un token único para esta orden
        )

        print(f"Nueva orden anulada creada con número de orden: {nueva_orden.numero_orden}")

        # Reiniciar sesión y crear un nuevo cliente anónimo
        if not request.user.is_authenticated:
            old_session_key = request.session.session_key
            request.session.flush()
            request.session.create()
            new_session_key = request.session.session_key

            print(f"Session key reiniciado (error): {old_session_key} -> {new_session_key}")

            nuevo_cliente_anonimo = ClienteAnonimo.objects.create(
                nombre="Anónimo",
                apellido="",
                email=f"anonimo_{new_session_key}@example.com",
                numero_telefono="",
                session_key=new_session_key
            )
            print(f"Nuevo cliente anónimo creado (error): {nuevo_cliente_anonimo.email} con session_key: {new_session_key}")

        contexto = {'mensaje_error': f"Error al procesar la transacción: {e.message}"}
        return render(request, 'Transaccion/retorno_webpay.html', contexto)

