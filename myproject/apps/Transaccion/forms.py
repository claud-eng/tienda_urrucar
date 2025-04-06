import datetime # Importa 'datetime' para trabajar con fechas y horas.
from apps.Usuario.forms import ClienteAnonimoForm  # Importa el formulario para clientes anónimos desde la app Usuario.
from django import forms  # Importa el módulo forms de Django para crear formularios.
from django.core.exceptions import ValidationError  # Importa ValidationError para manejar errores de validación en formularios.
from django.forms import DateTimeInput  # Importa DateTimeInput para widgets de entrada de fecha y hora.
from django.forms import inlineformset_factory  # Importa inlineformset_factory para crear formularios en línea para modelos relacionados.
from django.forms.widgets import DateInput  # Importa DateInput para widgets de entrada de fecha.
from .models import Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto, Servicio  # Importa los modelos Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto y Servicio de la aplicación actual.

# Formulario para gestionar la creación y actualización de productos
class ProductoForm(forms.ModelForm):
    CONSIGNADO_CHOICES = [
        ('True', "Sí"),   # "Sí" es la primera opción predeterminada
        ('False', "No"),
    ]

    consignado = forms.ChoiceField(
        choices=CONSIGNADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_consignado'}),
        label="Stock Propio"
    )

    class Meta:
        model = Producto
        fields = [
            'nombre', 'marca', 'modelo', 'version', 'anio',
            'categoria', 'descripcion', 'precio_reserva', 'precio',
            'precio_costo', 'costo_extra', 'fecha_adquisicion', 'cantidad_stock',
            'imagen', 'consignado', 'porcentaje_consignacion'
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'fecha_adquisicion': DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'porcentaje_consignacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'id': 'id_porcentaje_consignacion'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        print(f"Inicializando ProductoForm con Producto ID: {self.instance.id}")
        print(f"Consignado en la BD: {self.instance.consignado}")
        print(f"Porcentaje Consignación en la BD: {self.instance.porcentaje_consignacion}")

        # Convertir booleano a string para ChoiceField
        if self.instance.pk is None:  # Si es un nuevo producto (aún no se ha guardado en la BD)
            self.initial['consignado'] = 'True'  # Valor predeterminado: Sí (Stock Propio)
        else:
            self.initial['consignado'] = 'True' if self.instance.consignado else 'False'

        # Si hay un valor en la BD, asignarlo
        if self.instance.porcentaje_consignacion is not None:
            self.initial['porcentaje_consignacion'] = self.instance.porcentaje_consignacion
        else:
            self.initial['porcentaje_consignacion'] = 0  # Asegurar que haya un valor en el input

    def clean_consignado(self):
        """
        Convierte la selección de "Sí" o "No" en un valor booleano real.
        """
        valor = self.cleaned_data.get("consignado")
        print(f"\nClean Consignado - Valor recibido: {valor}")

        resultado = valor == "True"
        print(f"Clean Consignado - Convertido a booleano: {resultado}")
        return resultado
    
    def clean_imagen(self):
        """
        Valida que la imagen principal no supere los 3 MB.
        """
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            if imagen.size > 3 * 1024 * 1024:
                raise ValidationError("La imagen no puede superar los 3 MB.")
        return imagen

    def clean_porcentaje_consignacion(self):
        """
        Valida que el porcentaje de consignación solo sea obligatorio si `consignado` es False.
        """
        consignado = self.cleaned_data.get("consignado")
        porcentaje = self.cleaned_data.get("porcentaje_consignacion")

        print(f"\nClean Porcentaje - Stock Propio: {consignado}, Porcentaje Consignación recibido: {porcentaje}")

        if consignado:
            print("Producto es Stock Propio, forzando porcentaje a 0")
            return 0  

        if not consignado and (porcentaje is None or porcentaje == ""):
            print("Error: Producto no es Stock Propio pero no tiene porcentaje")
            raise forms.ValidationError("Debe ingresar un porcentaje de consignación si el producto no es stock propio.")
        
        if porcentaje is not None and (porcentaje < 0 or porcentaje > 100):
            print("Error: Porcentaje fuera de rango")
            raise forms.ValidationError("El porcentaje de consignación debe estar entre 0 y 100.")

        print(f"Porcentaje válido: {porcentaje}")
        return porcentaje

    def clean_categoria(self):
        """
        Valida que la categoría no sea 'Sin categoría'.
        """
        categoria = self.cleaned_data.get('categoria')
        if categoria == "Sin categoría":
            raise forms.ValidationError("Debe seleccionar una categoría válida.")
        return categoria

    def clean_fecha_adquisicion(self):
        """
        Valida que la fecha de adquisición no sea futura.
        """
        fecha_adquisicion = self.cleaned_data.get('fecha_adquisicion')
        if fecha_adquisicion and fecha_adquisicion > datetime.date.today():
            raise forms.ValidationError("La fecha de adquisición no puede estar en el futuro.")
        return fecha_adquisicion

    def clean(self):
        """
        Limpia y formatea los datos ingresados.
        """
        cleaned_data = super().clean()  # Llama a la limpieza predeterminada del formulario
        
        # Obtener datos
        nombre = cleaned_data.get('nombre')
        marca = cleaned_data.get('marca')
        modelo = cleaned_data.get('modelo')
        version = cleaned_data.get('version')
        anio = cleaned_data.get('anio')
        descripcion = cleaned_data.get('descripcion')

        # Validar que el año sea razonable
        if anio and (anio < 1900 or anio > datetime.date.today().year + 1):
            self.add_error('anio', "El año debe estar entre 1900 y el próximo año.")

        return cleaned_data  # Retorna los datos limpios y formateados

class ImagenProductoForm(forms.ModelForm):
    class Meta:
        model = ImagenProducto
        fields = ['imagen']
        widgets = {
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),  # Sin `multiple`
        }

    def clean_imagen(self):
        """
        Valida que la imagen adicional no supere los 3 MB.
        """
        imagen = self.cleaned_data.get('imagen')
        if imagen:
            if imagen.size > 3 * 1024 * 1024:  # 3 MB
                raise ValidationError("La imagen no puede superar los 3 MB.")
        return imagen

# Formulario para gestionar la creación y actualización de servicios
class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'precio', 'imagen']  # Incluimos la imagen
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        # Define los widgets y atributos de clase según tus necesidades

    def clean(self):
        # Método para limpiar y formatear los datos ingresados
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        descripcion = cleaned_data.get('descripcion')

        # Capitaliza los campos de texto para consistencia en el formato
        if nombre:
            cleaned_data['nombre'] = nombre.capitalize()
        if descripcion:
            cleaned_data['descripcion'] = descripcion.capitalize()

        return cleaned_data

# Formulario para ventas online
class VentaOnlineForm(forms.ModelForm):
    class Meta:
        model = VentaOnline
        fields = ['cliente', 'total', 'estado', 'tipo_pago', 'numero_cuotas', 'monto_cuotas']

# Formulario de detalle para ventas online
class DetalleVentaOnlineForm(forms.ModelForm):
    class Meta:
        model = DetalleVentaOnline
        fields = ['producto', 'cantidad', 'precio', 'estado_reserva']

# Formulario para ventas manuales (cliente anónimo)
class VentaManualForm(forms.ModelForm):

    fecha_pago_final = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Fecha Pago Completo"
    )

    class Meta:
        model = VentaManual
        fields = ['pago_cliente', 'precio_personalizado', 'fecha_creacion']
        labels = {
            'pago_cliente': 'Monto Pagado por el Cliente',
            'precio_personalizado': 'Valor Total del Vehículo (IVA incluido)',
            'fecha_creacion': 'Fecha de la Venta',
            'fecha_pago_final': 'Fecha Pago Completo'
        }
        widgets = {
            'pago_cliente': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_personalizado': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_creacion': DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'fecha_pago_final': DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def save(self, commit=True):
        venta = super().save(commit=False)

        # Si es un nuevo registro, toma `fecha_creacion` del formulario
        if not self.instance.pk:
            venta.fecha_creacion = self.cleaned_data.get('fecha_creacion')
            print("Nueva venta, fecha_creacion tomada del formulario:", venta.fecha_creacion)
        else:
            # Si es una edición, preservar `fecha_creacion` del objeto existente
            venta.fecha_creacion = self.instance.fecha_creacion
            print("Edición de venta, fecha_creacion preservada:", venta.fecha_creacion)

        # Evitar errores si precio_personalizado es None
        venta.precio_personalizado = self.cleaned_data.get('precio_personalizado', 0) or 0
        venta.pago_cliente = self.cleaned_data.get('pago_cliente', 0) or 0

        # Verificar si el pago cubre el total antes de asignar la fecha
        if venta.pago_cliente >= venta.precio_personalizado:
            venta.fecha_pago_final = self.cleaned_data.get('fecha_pago_final', None)
            print("Fecha de pago final editada:", venta.fecha_pago_final)
        else:
            venta.fecha_pago_final = None  # Resetear si no se ha pagado completamente
            print("Pago incompleto, fecha de pago final reseteada a None")

        if commit:
            venta.save()
        return venta

# Formulario de detalle de productos en venta manual
class DetalleVentaManualProductoForm(forms.ModelForm):
    producto = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='ID del Producto',
        required=True
    )

    class Meta:
        model = DetalleVentaManual
        fields = ['producto']

    def clean_producto(self):
        """
        Valida que el producto ingresado exista en la base de datos.
        """
        id_producto = self.cleaned_data.get('producto')
        try:
            return Producto.objects.get(id=id_producto)
        except Producto.DoesNotExist:
            raise forms.ValidationError("No se encontró un producto con ese ID.")
        
# Formulario de detalle de servicios en venta manual
class DetalleVentaManualServicioForm(forms.ModelForm):
    servicio = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='ID del Servicio',
        required=False  # Permitir que sea opcional al editar
    )
    precio_costo = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Valor Costo',
        required=True,
        min_value=0,
        help_text="Valor de Compra asociado a este servicio en esta venta.",
        initial=0
    )

    marca_vehiculo = forms.CharField(
        required=False,
        label="Marca",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    modelo_vehiculo = forms.CharField(
        required=False,
        label="Modelo",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    patente_vehiculo = forms.CharField(
        required=False,
        label="Patente",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = DetalleVentaManual
        fields = ['servicio', 'precio_costo', 'marca_vehiculo', 'modelo_vehiculo', 'patente_vehiculo']

    def clean_servicio(self):
        id_servicio = self.cleaned_data.get('servicio')
        if id_servicio:  # Si se proporciona un nuevo ID de servicio
            try:
                return Servicio.objects.get(id=id_servicio)
            except Servicio.DoesNotExist:
                raise ValidationError("Servicio no encontrado.")
        # Si no se proporciona un nuevo servicio, devuelve el existente
        if self.instance and self.instance.servicio:
            return self.instance.servicio
        raise ValidationError("Debe seleccionarse un servicio válido.")

# Formset para gestionar múltiples detalles en una venta online
DetalleVentaOnlineFormset = inlineformset_factory(
    VentaOnline,  # Modelo padre
    DetalleVentaOnline,  # Modelo hijo
    form=DetalleVentaOnlineForm,
    fields=('producto', 'cantidad', 'precio', 'estado_reserva'),
    extra=1,  # Número de formularios adicionales
    can_delete=True,  # Permitir eliminar ítems
)


