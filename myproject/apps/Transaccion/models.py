import os  # Importa el módulo 'os' para manejar operaciones relacionadas con el sistema de archivos y variables de entorno.
from apps.Usuario.models import Cliente, ClienteAnonimo, Empleado  # Importa las clases Cliente, ClienteAnonimo Empleado desde la aplicación Usuario.
from datetime import timedelta  # Permite crear y manipular diferencias de tiempo (duraciones).
from django.contrib.auth.models import User  # Importa el modelo User de Django para la gestión de usuarios.
from django.utils.deconstruct import deconstructible  # Importa el decorador 'deconstructible' para serialización en migraciones.
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation  # Importa campos genéricos para relaciones en modelos.
from django.contrib.contenttypes.models import ContentType  # Importa el modelo ContentType para gestionar tipos de contenido genéricos.
from django.db import models  # Importa la biblioteca models de Django para definir modelos.
from django.forms import ValidationError  # Importa ValidationError para manejar errores de validación en formularios.
from django.utils.timezone import now # Importa la función now para obtener la hora actual.

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
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)  # Imagen principal del producto
    precio_costo = models.PositiveIntegerField(null=True, blank=True, help_text="Precio de costo del producto")
    costo_extra = models.PositiveIntegerField(null=True, blank=True, help_text="Costos adicionales del producto")

    @property
    def ganancia(self):
        """Calcula la ganancia del producto dinámicamente."""
        if self.precio_costo is not None and self.costo_extra is not None:
            return self.precio - (self.precio_costo + self.costo_extra)
        return None

    def __str__(self):
        return self.nombre  # Retorna el nombre del producto como representación en cadena
    
# Valida que el tamaño de la imagen no supere los 3 MB.
def validar_tamano_imagen(image):
    if image.size > 3 * 1024 * 1024:  # 3 MB
        raise ValidationError("La imagen no puede superar los 3 MB.")

# Clase que representa una imagen adicional asociada a un producto
class ImagenProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='imagenes')
    imagen = models.ImageField(upload_to='galeria_productos/', validators=[validar_tamano_imagen])

    def save(self, *args, **kwargs):
        # Si ya existe una imagen, genera un nombre personalizado
        if self.imagen and not self.id:  # Evitar renombrar en actualizaciones
            # Obtén el nombre original y extensión del archivo
            nombre_original, extension = os.path.splitext(self.imagen.name)
            
            # Genera un nuevo nombre basado en el ID del producto
            nuevo_nombre = f"{nombre_original}_{self.producto.id}{extension}"
            
            # Asigna el nuevo nombre al campo 'imagen'
            self.imagen.name = nuevo_nombre
        
        # Llama al método save original
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Imagen de {self.producto.nombre}"

# Clase para almacenar información de servicios
class Servicio(models.Model):
    nombre = models.CharField(max_length=100)  # Nombre del servicio
    descripcion = models.TextField()  # Descripción del servicio
    precio = models.PositiveIntegerField()  # Precio del servicio
    imagen = models.ImageField(upload_to='servicios/', null=True, blank=True)  # Imagen principal del servicio

    def __str__(self):
        return self.nombre

# Clase para registrar los productos o servicios en el carrito de un cliente
class Carrito(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    cliente_anonimo = models.ForeignKey(ClienteAnonimo, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=255, null=True, blank=True)  # Identificador único para clientes anónimos
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey('content_type', 'object_id')
    cantidad = models.PositiveIntegerField()
    carrito = models.PositiveIntegerField(default=1)

    def obtener_precio_total(self):
        if isinstance(self.item, Producto) and self.item.categoria == "Vehículo":
            return self.item.precio_reserva * self.cantidad
        return self.item.precio * self.cantidad

# Clase para agregar relaciones inversas con Carrito
class ContenidoCarrito(models.Model):
    carrito = GenericRelation('Carrito')  # Relación inversa con Carrito

# Clase para almacenar ventas realizadas en línea
class VentaOnline(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Cliente registrado que realiza la compra (opcional para cliente anónimo)."
    )  # Cliente registrado
    cliente_anonimo = models.ForeignKey(
        ClienteAnonimo, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Cliente anónimo que realiza la compra."
    )  # Cliente anónimo
    productos = models.ManyToManyField(Producto, through='DetalleVentaOnline')  # Productos comprados
    servicios = models.ManyToManyField(Servicio, through='DetalleVentaOnline')  # Servicios comprados
    total = models.DecimalField(max_digits=10, decimal_places=2)  # Monto total
    fecha = models.DateTimeField(auto_now_add=True)  # Fecha de la transacción
    estado = models.CharField(max_length=20, default='pendiente')  # Estado de la venta
    token_ws = models.CharField(max_length=100, null=True, blank=True)  # Token de la transacción
    numero_orden = models.CharField(max_length=26, null=True, blank=True)  # Número de orden
    tipo_pago = models.CharField(max_length=30, null=True, blank=True)  # Tipo de pago (VD, VN, etc.)
    monto_cuotas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Monto por cuota
    numero_cuotas = models.PositiveIntegerField(null=True, blank=True)  # Número de cuotas

    def __str__(self):
        if self.cliente:
            return f"Venta Online - Cliente: {self.cliente.user.username}"
        elif self.cliente_anonimo:
            return f"Venta Online - Cliente Anónimo: {self.cliente_anonimo.nombre}"
        return f"Venta Online - Sin cliente asociado"

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
    fecha_estado_final = models.DateTimeField(null=True, blank=True)  # Fecha en la que se actualizó el estado final
    calculo_tiempo_transcurrido = models.PositiveIntegerField(null=True, blank=True)  # Días transcurridos

    def save(self, *args, **kwargs):
        # Si el estado cambia a 'Vendida' o 'Desistida' y no tiene fecha final, asignar la fecha actual
        if self.estado_reserva in ['Vendida', 'Desistida'] and not self.fecha_estado_final:
            self.fecha_estado_final = now()
            # Calcular el tiempo transcurrido en días
            if self.orden_compra.fecha and self.fecha_estado_final:
                diferencia = self.fecha_estado_final - self.orden_compra.fecha
                self.calculo_tiempo_transcurrido = max(diferencia.days, 0)  # Asignar 0 si es el mismo día
        elif self.estado_reserva not in ['Vendida', 'Desistida']:
            # Limpiar los campos si el estado no es final
            self.fecha_estado_final = None
            self.calculo_tiempo_transcurrido = None
        super().save(*args, **kwargs)

    @property
    def ganancia(self):
        """Calcula la ganancia del detalle."""
        if self.producto:
            if self.producto.categoria == "Vehículo" and self.estado_reserva == "Vendida":
                return self.producto.ganancia  # Usa el cálculo del modelo Producto
            return self.precio * self.cantidad  # Ganancia es el total del precio para otros productos
        elif self.servicio:
            return self.precio * self.cantidad  # Para servicios, considera el precio como ganancia directa
        return 0

    def __str__(self):
        return f"Detalle de {self.orden_compra.numero_orden}"

# Clase para almacenar ventas realizadas manualmente
class VentaManual(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Cliente registrado que realiza la compra (opcional para cliente anónimo)."
    )
    cliente_anonimo = models.ForeignKey(
        ClienteAnonimo, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Cliente anónimo que realiza la compra."
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)
    pago_cliente = models.PositiveIntegerField(default=0)
    cambio = models.PositiveIntegerField(default=0)
    precio_personalizado = models.PositiveIntegerField(null=True, blank=True, help_text="Precio personalizado si no se usa el precio de los servicios.")

    def calcular_total(self):
        """
        Calcula el total de la venta sumando subtotales de productos y servicios.
        """
        total_productos = sum(item.obtener_subtotal() for item in self.detalleventamanual_set.filter(producto__isnull=False))
        total_servicios = sum(item.obtener_subtotal() for item in self.detalleventamanual_set.filter(servicio__isnull=False))

        # Si el precio de servicios es 0, usar el precio personalizado
        self.total = total_servicios if total_servicios > 0 else (self.precio_personalizado or 0)

    def calcular_ganancia_total(self):
        """
        Calcula la ganancia total de la venta.
        En este caso, se utiliza el valor mostrado en "Total (IVA incluido)".
        """
        # Si el total es 0, usar el precio personalizado; de lo contrario, usar el total
        if self.total == 0:
            return self.precio_personalizado or 0
        return self.total

    def calcular_cambio(self):
        """
        Calcula el cambio a devolver al cliente.
        """
        self.cambio = self.pago_cliente - self.total

    def save(self, *args, **kwargs):
        """
        Guarda la instancia, calcula total y cambio después de guardar la instancia por primera vez.
        """
        # Si la instancia es nueva (no tiene un ID), guárdala primero para obtener un PK
        if not self.pk:
            super().save(*args, **kwargs)
        
        # Ahora que la instancia tiene un ID, calcula el total y el cambio
        self.calcular_total()
        self.calcular_cambio()
        
        # Guarda nuevamente con los valores calculados
        super().save(*args, **kwargs)

    def __str__(self):
        if self.cliente:
            return f"Orden {self.id} - Cliente: {self.cliente.user.username}"
        elif self.cliente_anonimo:
            return f"Orden {self.id} - Cliente Anónimo: {self.cliente_anonimo.nombre}"
        return f"Orden {self.id} - Sin cliente asociado"

# Clase para detallar cada ítem (producto o servicio) en la venta manual
class DetalleVentaManual(models.Model):
    orden_compra = models.ForeignKey(VentaManual, on_delete=models.CASCADE, related_name='detalleventamanual_set')  # Venta a la que pertenece
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)  # Producto en el detalle
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)  # Servicio en el detalle
    cantidad = models.PositiveIntegerField(default=1)  # Cantidad del ítem
    subtotal = models.PositiveIntegerField(default=0)  # Subtotal del ítem

    def obtener_subtotal(self):
        """
        Calcula el subtotal basado en la cantidad y precio del producto o servicio.
        """
        if self.producto:
            return self.producto.precio * self.cantidad
        elif self.servicio:
            return self.servicio.precio * self.cantidad
        return 0

    @property
    def ganancia(self):
        """
        Calcula la ganancia del detalle basado en el tipo de producto o servicio.
        """
        if self.producto:
            # Si es un vehículo y el precio costo y extra son válidos, calcular ganancia específica
            if self.producto.categoria == "Vehículo" and self.producto.precio_costo is not None and self.producto.costo_extra is not None:
                return (self.producto.precio - (self.producto.precio_costo + self.producto.costo_extra)) * self.cantidad
            # Para otros productos, la ganancia es el subtotal
            return self.obtener_subtotal()
        elif self.servicio:
            # Para servicios, considera el precio como ganancia directa
            return self.obtener_subtotal()
        return 0

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para calcular y guardar el subtotal y actualizar la venta asociada.
        """
        # Establece el subtotal antes de guardar
        self.subtotal = self.obtener_subtotal()
        super().save(*args, **kwargs)

        # Después de guardar, actualizar el total y cambio de la orden de venta
        if self.orden_compra_id:
            self.orden_compra.calcular_total()
            self.orden_compra.calcular_cambio()
            self.orden_compra.save()

    def __str__(self):
        """
        Representación en cadena del detalle, indicando producto o servicio y cantidad.
        """
        if self.producto:
            return f"{self.cantidad} x {self.producto.nombre}"
        elif self.servicio:
            return f"Servicio: {self.servicio.nombre}"

