from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation 
from django.contrib.contenttypes.models import ContentType
from django.db import models
from apps.Usuario.models import Cliente, Empleado  # Importa las clases Cliente y Empleado

# Create your models here.

# Clase para almacenar información de productos
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    categoria = models.CharField(max_length=100, null=True)
    descripcion = models.TextField()
    precio = models.PositiveIntegerField() 
    cantidad_stock = models.PositiveIntegerField()
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)

    def __str__(self):
        return self.nombre

# Clase para almacenar información de servicios
class Servicio(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.PositiveIntegerField() 

    def __str__(self):
        return self.nombre

# Clase para registrar los productos o servicios en el carrito de un cliente
class Carrito(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey('content_type', 'object_id')
    cantidad = models.PositiveIntegerField()
    carrito = models.PositiveIntegerField(default=1)  # Agrega este campo para identificar carritos

    def __str__(self):
        return f'{self.cliente.username} - {self.item}'

    def obtener_precio_total(self):
        return self.item.precio * self.cantidad

class ContenidoCarrito(models.Model):
    carrito = GenericRelation('Carrito')  # Agrega este campo para la relación inversa

class OrdenDeCompra(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    productos = models.ManyToManyField(Producto, through='DetalleOrdenCompra')  # Utilizamos una relación ManyToMany a través de un modelo intermedio
    servicios = models.ManyToManyField(Servicio, through='DetalleOrdenCompra')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, default='pendiente')  # Puede ser pendiente, aprobada, rechazada, etc.
    token_ws = models.CharField(max_length=100, null=True, blank=True)
    numero_orden = models.CharField(max_length=26, null=True, blank=True)
    tipo_pago = models.CharField(max_length=30, null=True, blank=True)  # VD, VN, VC, etc.
    monto_cuotas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    numero_cuotas = models.PositiveIntegerField(null=True, blank=True)

class DetalleOrdenCompra(models.Model):
    orden_compra = models.ForeignKey(OrdenDeCompra, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveIntegerField()

class OrdenDeVenta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)
    pago_cliente = models.PositiveIntegerField(default=0)
    cambio = models.PositiveIntegerField(default=0)

    def calcular_total(self):
        total_productos = sum(item.obtener_subtotal() for item in self.detalleordenventa_set.filter(producto__isnull=False))
        total_servicios = sum(item.obtener_subtotal() for item in self.detalleordenventa_set.filter(servicio__isnull=False))
        self.total = total_productos + total_servicios

    def calcular_cambio(self):
        self.cambio = self.pago_cliente - self.total

    def save(self, *args, **kwargs):
        # Guarda primero la instancia para obtener un ID de clave primaria.
        super().save(*args, **kwargs)
        # Ahora que tenemos un ID, podemos calcular el total y el cambio.
        self.calcular_total()
        self.calcular_cambio()
        # Guarda de nuevo la instancia para actualizar el total y el cambio.
        # Esto asegura que no entramos en un bucle infinito de guardados.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden {self.id} - Cliente: {self.cliente.user.username}"

    def __str__(self):
        return f"Orden {self.id} - Cliente: {self.cliente.user.username}"

class DetalleOrdenVenta(models.Model):
    orden_venta = models.ForeignKey(OrdenDeVenta, on_delete=models.CASCADE, related_name='detalleordenventa_set')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    subtotal = models.PositiveIntegerField(default=0)

    def obtener_subtotal(self):
        if self.producto:
            return self.producto.precio * self.cantidad
        elif self.servicio:
            return self.servicio.precio * self.cantidad
        return 0

    def save(self, *args, **kwargs):
        # Establece el subtotal antes de guardar.
        self.subtotal = self.obtener_subtotal()
        print(f"Guardando DetalleOrdenVenta: {self.producto}, Cantidad: {self.cantidad}, Subtotal: {self.subtotal}")
        super().save(*args, **kwargs)
        # Después de guardar, actualizamos el total de la orden de venta.
        if self.orden_venta_id:
            self.orden_venta.calcular_total()
            self.orden_venta.calcular_cambio()
            self.orden_venta.save()

    def __str__(self):
        if self.producto:
            return f"{self.cantidad} x {self.producto.nombre}"
        elif self.servicio:
            return f"Servicio: {self.servicio.nombre}"