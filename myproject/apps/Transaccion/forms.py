import datetime # Importa 'datetime' para trabajar con fechas y horas.
from django import forms  # Importa el módulo forms de Django para crear formularios.
from django.core.exceptions import ValidationError  # Importa ValidationError para manejar errores de validación en formularios.
from django.forms import inlineformset_factory  # Importa inlineformset_factory para crear formularios en línea para modelos relacionados.
from .models import Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto, Servicio  # Importa los modelos Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto y Servicio de la aplicación actual.

# Formulario para cliente anónimo
class ClienteAnonimoForm(forms.ModelForm):
    class Meta:
        model = ClienteAnonimo
        fields = ['nombre', 'apellido', 'email', 'numero_telefono']
        
# Formulario para gestionar la creación y actualización de productos
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto  # Especifica el modelo asociado
        fields = [
            'nombre', 'marca', 'modelo', 'version', 'anio',
            'categoria', 'descripcion', 'precio', 'precio_reserva',
            'cantidad_stock', 'imagen'
        ]
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-control'}),  # Usa un select con clases Bootstrap
        }

    def __init__(self, *args, **kwargs):
        # Inicializa el formulario
        super().__init__(*args, **kwargs)

    def clean_categoria(self):
        """
        Valida que la categoría no sea 'Sin categoría'.
        """
        categoria = self.cleaned_data.get('categoria')
        if categoria == "Sin categoría":
            raise forms.ValidationError("Debe seleccionar una categoría válida.")
        return categoria

    def clean(self):
        # Método para limpiar y formatear los datos ingresados
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
        fields = ['pago_cliente']
        widgets = {
            'pago_cliente': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        # Lógica para asociar a cliente anónimo
        venta = super().save(commit=False)
        if commit:
            venta.save()
        return venta

# Formulario de detalle de productos en venta manual
class DetalleVentaManualProductoForm(forms.ModelForm):
    producto = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='ID del Producto'
    )

    class Meta:
        model = DetalleVentaManual
        fields = ['producto', 'cantidad']

    def clean_producto(self):
        id_producto = self.cleaned_data['producto']
        try:
            return Producto.objects.get(id=id_producto)
        except Producto.DoesNotExist:
            raise ValidationError("Producto no encontrado.")

# Formulario de detalle de servicios
class DetalleVentaManualServicioForm(forms.ModelForm):
    servicio = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label='ID del Servicio'
    )

    class Meta:
        model = DetalleVentaManual
        fields = ['servicio']
    
    def clean_servicio(self):
        id_servicio = self.cleaned_data['servicio']
        try:
            return Servicio.objects.get(id=id_servicio)
        except Servicio.DoesNotExist:
            raise ValidationError("Servicio no encontrado.")

# Formset para gestionar múltiples detalles en una venta online
DetalleVentaOnlineFormset = inlineformset_factory(
    VentaOnline,  # Modelo padre
    DetalleVentaOnline,  # Modelo hijo
    form=DetalleVentaOnlineForm,
    fields=('producto', 'cantidad', 'precio', 'estado_reserva'),
    extra=1,  # Número de formularios adicionales
    can_delete=True,  # Permitir eliminar ítems
)

# Formset para gestionar múltiples detalles de productos en una venta manual
DetalleVentaManualProductoFormset = inlineformset_factory(
    VentaManual,  # Modelo padre (VentaManual)
    DetalleVentaManual,  # Modelo hijo (DetalleVentaManual)
    form=DetalleVentaManualProductoForm,  # Formulario para los detalles
    fields=('producto', 'cantidad',),  # Campos incluidos en el formset
    extra=1,  # Número de formularios adicionales para nuevas entradas
    can_delete=True  # Permite eliminar entradas en el formset
)

# Formset para gestionar múltiples detalles de servicios en una venta manual
DetalleVentaManualServicioFormset = inlineformset_factory(
    VentaManual,  # Modelo padre (VentaManual)
    DetalleVentaManual,  # Modelo hijo (DetalleVentaManual)
    form=DetalleVentaManualServicioForm,  # Formulario para los detalles de servicios
    fields=('servicio',),  # Campo incluido en el formset
    extra=1,  # Número de formularios adicionales para nuevas entradas
    can_delete=True  # Permite eliminar entradas en el formset
)
