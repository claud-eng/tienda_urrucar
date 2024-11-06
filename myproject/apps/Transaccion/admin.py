from django.contrib import admin
from .models import Producto, Servicio, Carrito, OrdenDeCompra, DetalleOrdenCompra, OrdenDeVenta, DetalleOrdenVenta

# Register your models here.

admin.site.register(Producto)
admin.site.register(Servicio)
admin.site.register(Carrito)
admin.site.register(OrdenDeCompra)
admin.site.register(DetalleOrdenCompra)
admin.site.register(OrdenDeVenta)
admin.site.register(DetalleOrdenVenta)