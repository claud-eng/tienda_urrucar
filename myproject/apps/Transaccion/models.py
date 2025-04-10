import os  # Importa el módulo 'os' para manejar operaciones relacionadas con el sistema de archivos y variables de entorno.
from apps.Usuario.models import Cliente, ClienteAnonimo, Empleado  # Importa las clases Cliente, ClienteAnonimo Empleado desde la aplicación Usuario.
from datetime import timedelta, timezone  # Permite crear y manipular diferencias de tiempo (duraciones).
from django.contrib.auth.models import User  # Importa el modelo User de Django para la gestión de usuarios.
from django.utils.deconstruct import deconstructible  # Importa el decorador 'deconstructible' para serialización en migraciones.
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation  # Importa campos genéricos para relaciones en modelos.
from django.contrib.contenttypes.models import ContentType  # Importa el modelo ContentType para gestionar tipos de contenido genéricos.
from django.db import models  # Importa la biblioteca models de Django para definir modelos.
from django.forms import ValidationError  # Importa ValidationError para manejar errores de validación en formularios.
from django.utils.timezone import now # Importa la función now para obtener la hora actual.

# Valida que el tamaño de la imagen no supere los 3 MB.
def validar_tamano_imagen(image):
    if image.size > 3 * 1024 * 1024:  # 3 MB
        raise ValidationError("La imagen no puede superar los 3 MB.")
    
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
    patente = models.CharField(max_length=20, null=True, blank=True) # Patente del vehículo
    categoria = models.CharField(
        max_length=100,
        choices=CATEGORIA_CHOICES,
        default='Sin categoría'  # Predeterminado: Sin categoría
    )  # Categoría a la que pertenece el producto
    descripcion = models.TextField()  # Descripción del producto
    precio = models.PositiveIntegerField()  # Precio normal del producto
    precio_reserva = models.PositiveIntegerField(null=True, blank=True)  # Precio de reserva del producto
    cantidad_stock = models.PositiveIntegerField()  # Cantidad disponible en stock
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True, validators=[validar_tamano_imagen])  # Imagen principal del producto
    precio_costo = models.PositiveIntegerField(null=True, blank=True, help_text="Precio de costo del producto")
    costo_extra = models.PositiveIntegerField(null=True, blank=True, help_text="Costos adicionales del producto")
    fecha_adquisicion = models.DateField(null=True, blank=True, help_text="Fecha en que se adquirió el producto")
    consignado = models.BooleanField(default=False, help_text="Indica si el producto está en consignación.")
    porcentaje_consignacion = models.DecimalField(
        max_digits=30, decimal_places=20, null=True, blank=True,
        help_text="Porcentaje de ganancia sobre el precio de venta para productos consignados."
    )

    @property
    def ganancia(self):
        """Calcula la ganancia del producto dinámicamente."""
        print(f"\n--- DEBUG: Calculando ganancia para {self.nombre} (ID: {self.id}) ---")
        print(f"Stock Propio (consignado): {self.consignado}")
        print(f"Precio Venta: {self.precio}")
        print(f"Valor de Compra: {self.precio_costo}")
        print(f"Costo Extra: {self.costo_extra}")
        print(f"Porcentaje Consignación: {self.porcentaje_consignacion}")

        if self.consignado:
            if self.porcentaje_consignacion is not None:
                ganancia = self.precio * (self.porcentaje_consignacion / 100)
                print(f"Ganancia Calculada (Consignación): {ganancia}")  # Depuración
                return ganancia
            print("Producto consignado pero sin porcentaje definido.")
            return 0  # Si no hay porcentaje definido, no hay ganancia
        else:
            if self.precio_costo is not None and self.costo_extra is not None:
                ganancia = self.precio - (self.precio_costo + self.costo_extra)
                print(f"Ganancia Calculada (Stock Propio): {ganancia}")  # Depuración
                return ganancia

        print("No se pudo calcular ganancia.")  # Depuración en caso de error
        return None

    def __str__(self):
        return self.nombre  # Retorna el nombre del producto como representación en cadena
    
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
    tbk_token = models.CharField(max_length=100, null=True, blank=True)  # Token de anulación de Webpay
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
    dias_desde_adquisicion = models.PositiveIntegerField(null=True, blank=True, help_text="Días transcurridos desde la adquisición del producto") # Días transcurridos entre la fecha de adquisición del producto y actualización de estado de reserva en la venta
    calculo_tiempo_transcurrido = models.PositiveIntegerField(null=True, blank=True)  # Días transcurridos entre la fecha de la transacción y actualización de estado de reserva en la venta
    marca_vehiculo = models.CharField(max_length=100, blank=True, null=True) # Marca del vehículo
    modelo_vehiculo = models.CharField(max_length=100, blank=True, null=True) # Modelo del vehículo
    patente_vehiculo = models.CharField(max_length=20, blank=True, null=True) # Patente del vehículo

    def save(self, *args, **kwargs):
        # Si el estado cambia a 'Vendida', actualiza la fecha_estado_final
        if self.estado_reserva == 'Vendida':
            if not self.fecha_estado_final:
                self.fecha_estado_final = now()

            # Calcular los días desde la adquisición del producto
            if self.producto and self.producto.fecha_adquisicion and self.fecha_estado_final:
                diferencia_adquisicion = self.fecha_estado_final.date() - self.producto.fecha_adquisicion
                self.dias_desde_adquisicion = max(diferencia_adquisicion.days, 0)

            # Calcular los días desde la transacción hasta la fecha final
            if self.orden_compra.fecha and self.fecha_estado_final:
                diferencia_reserva = self.fecha_estado_final - self.orden_compra.fecha
                self.calculo_tiempo_transcurrido = max(diferencia_reserva.days, 0)

        elif self.estado_reserva == 'Desistida':
            # Si el estado es 'Desistida', limpiar o asignar valores correspondientes
            self.dias_desde_adquisicion = 0
            if not self.fecha_estado_final:
                self.fecha_estado_final = now()  # Registrar fecha actual para "Desistida"
            self.calculo_tiempo_transcurrido = None  # Opcional, según lo necesites

        else:
            # Si el estado no es 'Vendida' ni 'Desistida', limpiar los campos
            self.fecha_estado_final = None
            self.calculo_tiempo_transcurrido = None
            self.dias_desde_adquisicion = None

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

class VentaManual(models.Model):
    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Cliente registrado que realiza la compra (opcional para cliente anónimo)."
    )
    cliente_anonimo = models.ForeignKey(
        ClienteAnonimo, on_delete=models.CASCADE, null=True, blank=True,
        help_text="Cliente anónimo que realiza la compra."
    )
    fecha_creacion = models.DateTimeField(null=True, blank=True, help_text="Fecha en que se realizó la venta.")
    fecha_pago_final = models.DateTimeField(null=True, blank=True, help_text="Fecha en que el pago fue completado.")
    total = models.PositiveIntegerField(default=0)
    pago_cliente = models.PositiveIntegerField(default=0)
    cambio = models.PositiveIntegerField(default=0)
    precio_personalizado = models.PositiveIntegerField(null=True, blank=True, help_text="Precio personalizado si no se usa el precio de los servicios.")

    def calcular_total(self):
        """
        Calcula el total de la venta sumando subtotales de productos y servicios o usando el precio personalizado.
        """
        if not self.pk:
            # Si la instancia aún no tiene un ID, no puede acceder a la relación
            return self.precio_personalizado or 0

        total_servicios = sum(item.obtener_subtotal() for item in self.detalleventamanual_set.filter(servicio__isnull=False))
        return total_servicios if total_servicios > 0 else (self.precio_personalizado or 0)

    def calcular_cambio(self):
        """
        Calcula el cambio a devolver al cliente.
        """
        return max(self.pago_cliente - self.total, 0)

    def save(self, *args, **kwargs):
        from django.utils import timezone  # Importación local, solo dentro del método

        print("Guardando instancia de VentaManual...")
        print(f"Fecha creación inicial: {self.fecha_creacion}")
        print(f"Fecha pago final inicial: {self.fecha_pago_final}")

        # Siempre recalcular total y cambio
        self.total = self.calcular_total()
        self.cambio = self.calcular_cambio()

        # Validación de fecha de pago final
        if self.pago_cliente >= self.total:
            if not self.fecha_pago_final:
                self.fecha_pago_final = timezone.localtime()
                print("Fecha de pago final actualizada a:", self.fecha_pago_final)
        else:
            if self.fecha_pago_final:
                print("Reset de fecha_pago_final porque el pago ya no es suficiente")
            self.fecha_pago_final = None

        print(f"Fecha creación final: {self.fecha_creacion}")
        print(f"Fecha pago final final: {self.fecha_pago_final}")

        super().save(*args, **kwargs)

    def __str__(self):
        if self.cliente:
            return f"Orden {self.id} - Cliente: {self.cliente.user.username}"
        elif self.cliente_anonimo:
            return f"Orden {self.id} - Cliente Anónimo: {self.cliente_anonimo.nombre}"
        return f"Orden {self.id} - Sin cliente asociado"

class DetalleVentaManual(models.Model):
    orden_compra = models.ForeignKey(VentaManual, on_delete=models.CASCADE, related_name='detalleventamanual_set')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_costo = models.PositiveIntegerField(null=True, blank=True, help_text="Costo asociado a este detalle")
    subtotal = models.PositiveIntegerField(default=0)
    marca_vehiculo = models.CharField(max_length=100, blank=True, null=True) # Marca del vehículo
    modelo_vehiculo = models.CharField(max_length=100, blank=True, null=True) # Modelo del vehículo
    patente_vehiculo = models.CharField(max_length=20, blank=True, null=True) # Patente del vehículo
    
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
        return self.obtener_subtotal() - (self.precio_costo or 0)

    def save(self, *args, **kwargs):
        """
        Guarda el detalle y calcula el subtotal.
        """
        # Calcular subtotal antes de guardar
        self.subtotal = self.obtener_subtotal()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.producto:
            return f"{self.cantidad} x {self.producto.nombre}"
        elif self.servicio:
            return f"Servicio: {self.servicio.nombre}"

# Clase para almacenar el código del presupuesto
class Presupuesto(models.Model):
    numero_presupuesto = models.CharField(max_length=10, unique=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.numero_presupuesto:
            ultimo = Presupuesto.objects.order_by("-id").first()
            if ultimo:
                nuevo_numero = str(int(ultimo.numero_presupuesto) + 1).zfill(10)
            else:
                nuevo_numero = "0000000001"
            self.numero_presupuesto = nuevo_numero
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Presupuesto {self.numero_presupuesto}"

# Clase para almacenar el código interno de la inspección
class InformeInspeccion(models.Model):
    codigo_interno = models.CharField(max_length=10, unique=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.codigo_interno:
            ultimo = InformeInspeccion.objects.order_by("-id").first()
            if ultimo:
                nuevo_codigo = str(int(ultimo.codigo_interno) + 1).zfill(10)
            else:
                nuevo_codigo = "0000000001"
            self.codigo_interno = nuevo_codigo
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inspección {self.codigo_interno}"