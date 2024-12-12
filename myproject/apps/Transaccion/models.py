from django.contrib.auth.models import User  # Importa el modelo User de Django para la gestión de usuarios.
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation  # Importa campos genéricos para relaciones en modelos.
from django.contrib.contenttypes.models import ContentType  # Importa el modelo ContentType para gestionar tipos de contenido genéricos.
from django.db import models  # Importa la biblioteca models de Django para definir modelos.
from apps.Usuario.models import Cliente, Empleado  # Importa las clases Cliente y Empleado de la aplicación Usuario.

# Clase para almacenar información de productos
class Producto(models.Model):
    # Opciones de categoría para el producto
    CATEGORIA_CHOICES = [
        ('Vehículo', 'Vehículo'),  # Categoría Vehículo
        ('Otro', 'Otro'),  # Categoría Otro
        ('Sin categoría', 'Sin categoría'),  # Nueva opción predeterminada
    ]

    nombre = models.CharField(max_length=100)  # Nombre del producto
    marca = models.CharField(max_length=100)  # Marca del producto
    modelo = models.CharField(max_length=100, null=True, blank=True)  # Modelo del producto
    version = models.CharField(max_length=50, null=True, blank=True)  # Versión del producto
    anio = models.PositiveIntegerField(null=True, blank=True)  # Año del producto
    categoria = models.CharField(
        max_length=100,
        choices=CATEGORIA_CHOICES,
        default='Sin categoría'  # Predeterminado: Sin categoría
    )  # Categoría a la que pertenece el producto
    descripcion = models.TextField()  # Descripción del producto
    precio = models.PositiveIntegerField()  # Precio normal del producto
    precio_reserva = models.PositiveIntegerField(null=True, blank=True)  # Precio de reserva del producto
    cantidad_stock = models.PositiveIntegerField()  # Cantidad disponible en stock
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)  # Imagen del producto

    def __str__(self):
        return self.nombre  # Retorna el nombre del producto como representación en cadena

# Clase para almacenar información de servicios
class Servicio(models.Model):
    nombre = models.CharField(max_length=100)  # Nombre del servicio
    descripcion = models.TextField()  # Descripción del servicio
    precio = models.PositiveIntegerField()  # Precio del servicio

    def __str__(self):
        return self.nombre  # Retorna el nombre del servicio como representación en cadena

# Clase para registrar los productos o servicios en el carrito de un cliente
class Carrito(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)  # Cliente asociado al carrito
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # Tipo de contenido (Producto o Servicio)
    object_id = models.PositiveIntegerField()  # ID del objeto (Producto o Servicio)
    item = GenericForeignKey('content_type', 'object_id')  # Relación genérica con Producto o Servicio
    cantidad = models.PositiveIntegerField()  # Cantidad de este ítem en el carrito
    carrito = models.PositiveIntegerField(default=1)  # Identificador de carrito, 1 indica carrito activo

    def __str__(self):
        return f'{self.cliente.username} - {self.item}'  # Retorna el cliente y el ítem en el carrito

    def obtener_precio_total(self):
        if isinstance(self.item, Producto) and self.item.categoria == "Vehículo":
            return self.item.precio_reserva * self.cantidad # Calcula el precio total para este ítem en el carrito
        return self.item.precio * self.cantidad 

# Clase para agregar relaciones inversas con Carrito
class ContenidoCarrito(models.Model):
    carrito = GenericRelation('Carrito')  # Relación inversa con Carrito

# Clase para almacenar ventas realizadas en línea
class VentaOnline(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)  # Cliente que realiza la compra
    productos = models.ManyToManyField(Producto, through='DetalleVentaOnline')  # Productos comprados en la venta
    servicios = models.ManyToManyField(Servicio, through='DetalleVentaOnline')  # Servicios comprados en la venta
    total = models.DecimalField(max_digits=10, decimal_places=2)  # Monto total de la venta
    fecha = models.DateTimeField(auto_now_add=True)  # Fecha de la venta
    estado = models.CharField(max_length=20, default='pendiente')  # Estado de la venta (pendiente, aprobada, etc.)
    token_ws = models.CharField(max_length=100, null=True, blank=True)  # Token de la transacción
    numero_orden = models.CharField(max_length=26, null=True, blank=True)  # Número de orden asignado
    tipo_pago = models.CharField(max_length=30, null=True, blank=True)  # Tipo de pago (VD, VN, etc.)
    monto_cuotas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Monto por cuota
    numero_cuotas = models.PositiveIntegerField(null=True, blank=True)  # Número de cuotas

# Clase para detallar cada ítem (producto o servicio) en la venta en línea
class DetalleVentaOnline(models.Model):
    orden_compra = models.ForeignKey(VentaOnline, on_delete=models.CASCADE)  # Venta a la que pertenece el detalle
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)  # Producto en el detalle
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)  # Servicio en el detalle
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # Precio del ítem
    cantidad = models.PositiveIntegerField()  # Cantidad del ítem
    estado_reserva = models.CharField(
        max_length=20,
        choices=[('En proceso', 'En proceso'), ('Vendida', 'Vendida'), ('Desistida', 'Desistida')],
        null=True,
        blank=True
    )  # Estado de la reserva

    def __str__(self):
        return f"Detalle de {self.orden_compra.numero_orden}"

# Clase para almacenar ventas realizadas manualmente
class VentaManual(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)  # Cliente que realiza la compra
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación de la venta
    total = models.PositiveIntegerField(default=0)  # Total de la venta
    pago_cliente = models.PositiveIntegerField(default=0)  # Monto pagado por el cliente
    cambio = models.PositiveIntegerField(default=0)  # Cambio a devolver al cliente

    def calcular_total(self):
        # Calcula el total de la venta sumando productos y servicios
        total_productos = sum(item.obtener_subtotal() for item in self.detalleventamanual_set.filter(producto__isnull=False))
        total_servicios = sum(item.obtener_subtotal() for item in self.detalleventamanual_set.filter(servicio__isnull=False))
        self.total = total_productos + total_servicios

    def calcular_cambio(self):
        # Calcula el cambio a devolver al cliente
        self.cambio = self.pago_cliente - self.total

    def save(self, *args, **kwargs):
        # Guarda la instancia para obtener el ID de clave primaria
        super().save(*args, **kwargs)
        # Calcula el total y el cambio, y guarda nuevamente
        self.calcular_total()
        self.calcular_cambio()
        super().save(*args, **kwargs)  # Guarda la instancia para actualizar total y cambio

    def __str__(self):
        return f"Orden {self.id} - Cliente: {self.cliente.user.username}"  # Representación en cadena de la venta manual

# Clase para detallar cada ítem (producto o servicio) en la venta manual
class DetalleVentaManual(models.Model):
    orden_venta = models.ForeignKey(VentaManual, on_delete=models.CASCADE, related_name='detalleventamanual_set')  # Venta a la que pertenece
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)  # Producto en el detalle
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)  # Servicio en el detalle
    cantidad = models.PositiveIntegerField(default=1)  # Cantidad del ítem
    subtotal = models.PositiveIntegerField(default=0)  # Subtotal del ítem

    def obtener_subtotal(self):
        # Calcula el subtotal basado en la cantidad y precio del producto o servicio
        if self.producto:
            return self.producto.precio * self.cantidad
        elif self.servicio:
            return self.servicio.precio * self.cantidad
        return 0

    def save(self, *args, **kwargs):
        # Establece el subtotal antes de guardar
        self.subtotal = self.obtener_subtotal()
        print(f"Guardando DetalleVentaManual: {self.producto}, Cantidad: {self.cantidad}, Subtotal: {self.subtotal}")
        super().save(*args, **kwargs)
        # Después de guardar, actualiza el total y cambio de la orden de venta
        if self.orden_venta_id:
            self.orden_venta.calcular_total()
            self.orden_venta.calcular_cambio()
            self.orden_venta.save()

    def __str__(self):
        # Representación en cadena del detalle, indicando producto o servicio y cantidad
        if self.producto:
            return f"{self.cantidad} x {self.producto.nombre}"
        elif self.servicio:
            return f"Servicio: {self.servicio.nombre}"
