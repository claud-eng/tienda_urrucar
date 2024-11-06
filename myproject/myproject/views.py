from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render, redirect

def home(request):
    return render(request, 'base/index.html')

def index(request):
    context = {
        'hero_image_url': 'images/hero_1.jpg',
    }
    return render(request, 'index.html', context)

def sobre_nosotros(request):
    return render(request, 'about.html')

def carro(request):
    return render(request, 'cart.html')

def proceder_pago(request):
    return render(request, 'checkout.html')

def contactanos(request):
    return render(request, 'contact.html')

def tienda(request):
    return render(request, 'shop.html')

def producto_tienda(request):
    return render(request, 'shop-single.html')

def regreso_pago(request):
    return render(request, 'thankyou.html')

def preguntas_frecuentes(request):
    return render(request, 'preguntas_frecuentes.html')

def enviar_correo_formulario(request):
    success = False  # Indicador de éxito
    if request.method == 'POST':
        name = request.POST.get('name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        subject = request.POST.get('subject', 'Sin Asunto')
        message = request.POST.get('message')

        # Combina el nombre y apellido para el nombre completo
        full_name = f"{name} {last_name}"
        full_message = f"Nombre Completo: {full_name}\nCorreo: {email}\n\nMensaje:\n{message}"

        try:
            send_mail(
                subject=subject,
                message=full_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['czamorano@claudev.cl'],
                fail_silently=False,
            )
            success = True  # Cambia el indicador a True si se envió con éxito
        except Exception as e:
            print(f"Error al enviar correo: {e}")

    return render(request, 'contact.html', {'success': success})