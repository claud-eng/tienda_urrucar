from django.shortcuts import render

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