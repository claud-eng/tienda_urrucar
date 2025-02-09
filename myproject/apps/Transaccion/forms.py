import datetime # Importa 'datetime' para trabajar con fechas y horas.
from django import forms  # Importa el módulo forms de Django para crear formularios.
from django.core.exceptions import ValidationError  # Importa ValidationError para manejar errores de validación en formularios.
from django.forms import DateTimeInput  # Importa DateTimeInput para widgets de entrada de fecha y hora.
from django.forms import inlineformset_factory  # Importa inlineformset_factory para crear formularios en línea para modelos relacionados.
from django.forms.widgets import DateInput  # Importa DateInput para widgets de entrada de fecha.
from .models import Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto, Servicio  # Importa los modelos Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto y Servicio de la aplicación actual.

# Formulario para cliente anónimo
class ClienteAnonimoForm(forms.ModelForm):
    class Meta:
        model = ClienteAnonimo
        fields = ['nombre', 'apellido', 'email', 'numero_telefono']
        
# Formulario para gestionar la creación y actualización de productos
class ProductoForm(forms.ModelForm):
    CONSIGNADO_CHOICES = [
        ('False', "No"),
        ('True', "Sí"),
    ]

    consignado = forms.ChoiceField(
        choices=CONSIGNADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_consignado'}),
        label="¿Está en consignación?"
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
        return valor == "True"

    def clean_porcentaje_consignacion(self):
        """
        Valida que el porcentaje de consignación solo sea obligatorio si `consignado` es True.
        """
        consignado = self.cleaned_data.get("consignado")
        porcentaje = self.cleaned_data.get("porcentaje_consignacion")

        print(f"Clean - Consignado: {consignado}, Porcentaje Consignación: {porcentaje}")

        if consignado and porcentaje is None:
            raise forms.ValidationError("Debe ingresar un porcentaje de consignación si el producto está en consignación.")
        elif porcentaje and (porcentaje < 0 or porcentaje > 100):
            raise forms.ValidationError("El porcentaje de consignación debe estar entre 0 y 100.")
        
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

        # Capitaliza los campos de texto para consistencia en el formato
        if nombre:
            cleaned_data['nombre'] = nombre.capitalize()
        if marca:
            cleaned_data['marca'] = marca.capitalize()
        if modelo:
            cleaned_data['modelo'] = modelo.capitalize()
        if version:
            cleaned_data['version'] = version.capitalize()
        if descripcion:
            cleaned_data['descripcion'] = descripcion.capitalize()

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
    class Meta:
        model = VentaManual
        fields = ['pago_cliente', 'precio_personalizado', 'fecha_creacion']
        labels = {
            'pago_cliente': 'Monto Pagado por el Cliente',
            'precio_personalizado': 'Total (IVA incluido)',
            'fecha_creacion': 'Fecha de la Venta',
        }
        widgets = {
            'pago_cliente': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_personalizado': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_creacion': DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
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

        if commit:
            venta.save()
        return venta

# Formulario de detalle de servicios en venta manual
class DetalleVentaManualServicioForm(forms.ModelForm):
    servicio = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='ID del Servicio',
        required=False  # Permitir que sea opcional al editar
    )
    precio_costo = forms.DecimalField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='Precio de Costo',
        required=True,
        min_value=0,
        help_text="Precio de costo asociado a este servicio en esta venta."
    )

    class Meta:
        model = DetalleVentaManual
        fields = ['servicio', 'precio_costo']

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