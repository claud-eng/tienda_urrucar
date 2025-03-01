from apps.Transaccion.context_processors import formato_precio # Importa la función formato_precio de la aplicación Transacción
from apps.Transaccion.models import Producto # Importa la clase Producto de la aplicación Transacción
from django.conf import settings  # Configuración del proyecto, incluyendo parámetros de correo electrónico
from django.core.mail import send_mail  # Función para enviar correos electrónicos
from django.shortcuts import render, redirect  # Funciones para renderizar plantillas y redirigir URLs

# Vista para la página de inicio
def home(request):
    # Renderiza la plantilla de la página principal
    return render(request, 'base/index.html')

# Vista para la página principal
def index(request):
    productos_principales = Producto.objects.filter(
        cantidad_stock__gte=0,
        categoria='Vehículo'  # Filtro para solo traer vehículos
    ).order_by('-id')[:5]
    for producto in productos_principales:
        producto.precio_formateado = formato_precio(producto.precio)
    return render(request, 'index.html', {'productos_principales': productos_principales})

# Vista para la página "Sobre Nosotros"
def sobre_nosotros(request):
    # Renderiza la plantilla 'about.html'
    return render(request, 'about.html')

# Vista para la página de contacto
def contactanos(request):
    # Renderiza la plantilla 'contact.html'
    return render(request, 'contact.html')

# Vista para la página de preguntas frecuentes
def preguntas_frecuentes(request):
    # Renderiza la plantilla 'preguntas_frecuentes.html'
    return render(request, 'preguntas_frecuentes.html')

# Función para manejar el envío de un correo electrónico desde el formulario de contacto
def enviar_correo_formulario(request):
    success = False  # Indicador para determinar si el envío fue exitoso
    if request.method == 'POST':  # Verifica si el método de solicitud es POST
        # Obtiene los datos del formulario de contacto
        name = request.POST.get('name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        subject = request.POST.get('subject', 'Sin Asunto')  # Valor predeterminado si no se proporciona un asunto
        message = request.POST.get('message')

        # Combina el nombre y apellido en un nombre completo
        full_name = f"{name} {last_name}"
        # Crea el mensaje completo con el nombre, correo y el mensaje del formulario
        full_message = f"Nombre Completo: {full_name}\nCorreo: {email}\n\nMensaje:\n{message}"

        try:
            # Intenta enviar el correo electrónico con los detalles proporcionados
            send_mail(
                subject=subject,
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,  # Remitente configurado en settings
                recipient_list=['czamorano@claudev.cl'],  # Destinatario
                fail_silently=False,  # Lanza una excepción en caso de fallo
            )
            success = True  # Cambia el indicador de éxito a True si el correo se envía correctamente
        except Exception as e:
            # Si ocurre un error, se captura y se imprime en la consola
            print(f"Error al enviar correo: {e}")

    # Renderiza la plantilla 'contact.html' con el indicador de éxito para mostrar un mensaje al usuario
    return render(request, 'contact.html', {'success': success})
