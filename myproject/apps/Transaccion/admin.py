from django.contrib import admin  # Importa el módulo de administración de Django.
from .models import Producto, Servicio, Carrito, VentaOnline, DetalleVentaOnline, VentaManual, DetalleVentaManual  # Importa los modelos específicos de la aplicación para registrarlos en el panel de administración.

# Register your models here.
admin.site.register(Producto)
admin.site.register(Servicio)
admin.site.register(Carrito)
admin.site.register(VentaOnline)
admin.site.register(DetalleVentaOnline)
admin.site.register(VentaManual)
admin.site.register(DetalleVentaManual)