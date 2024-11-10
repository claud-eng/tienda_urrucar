from django import forms  # Importa el módulo forms de Django para crear formularios.
from django.core.exceptions import ValidationError  # Importa ValidationError para manejar errores de validación en formularios.
from django.forms import inlineformset_factory  # Importa inlineformset_factory para crear formularios en línea para modelos relacionados.
from .models import Cliente, DetalleVentaManual, VentaManual, Producto, Servicio  # Importa los modelos Cliente, DetalleVentaManual, VentaManual, Producto y Servicio de la aplicación actual.

# Formulario para gestionar la creación y actualización de productos
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto  # Especifica el modelo asociado
        fields = ['nombre', 'marca', 'categoria', 'descripcion', 'precio', 'cantidad_stock', 'imagen']  # Campos incluidos en el formulario
        # Define los widgets y atributos de clase según tus necesidades

    def clean(self):
        # Método para limpiar y formatear los datos ingresados
        cleaned_data = super().clean()  # Llama a la limpieza predeterminada del formulario
        nombre = cleaned_data.get('nombre')
        marca = cleaned_data.get('marca')
        categoria = cleaned_data.get('categoria')
        descripcion = cleaned_data.get('descripcion')

        # Capitaliza los campos de texto para consistencia en el formato
        if nombre:
            cleaned_data['nombre'] = nombre.capitalize()
        if marca:
            cleaned_data['marca'] = marca.capitalize()
        if categoria:
            cleaned_data['categoria'] = categoria.capitalize()
        if descripcion:
            cleaned_data['descripcion'] = descripcion.capitalize()

        return cleaned_data  # Retorna los datos limpios y formateados

# Formulario para gestionar la creación y actualización de servicios
class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio  # Especifica el modelo asociado
        fields = ['nombre', 'descripcion', 'precio']  # Campos incluidos en el formulario
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

# Formulario para registrar una venta manual, incluye el ID del cliente
class VentaManualForm(forms.ModelForm):
    cliente = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}), label='ID del Cliente')  # Campo para ingresar el ID del cliente

    class Meta:
        model = VentaManual  # Especifica el modelo asociado
        fields = ['cliente', 'pago_cliente']  # Campos incluidos en el formulario
        widgets = {
            'pago_cliente': forms.NumberInput(attrs={'class': 'form-control'}),  # Widget personalizado para el campo de pago
        }

    def clean_cliente(self):
        # Método para validar que el cliente existe en la base de datos
        id_cliente = self.cleaned_data['cliente']
        try:
            return Cliente.objects.get(id=id_cliente)  # Retorna el cliente si existe
        except Cliente.DoesNotExist:
            raise ValidationError("Cliente no encontrado.")  # Error si el cliente no existe

# Formulario para detalles de venta manual relacionados con productos
class DetalleVentaManualForm(forms.ModelForm):
    producto = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}), label='ID del Producto')  # Campo para ingresar el ID del producto

    class Meta:
        model = DetalleVentaManual  # Especifica el modelo asociado
        fields = ['producto', 'cantidad']  # Campos incluidos en el formulario
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),  # Widget personalizado para el campo de cantidad
        }

    def clean_producto(self):
        # Método para validar que el producto existe en la base de datos
        id_producto = self.cleaned_data['producto']
        try:
            return Producto.objects.get(id=id_producto)  # Retorna el producto si existe
        except Producto.DoesNotExist:
            raise ValidationError("Producto no encontrado.")  # Error si el producto no existe

# Formulario para detalles de venta manual relacionados con servicios
class DetalleVentaManualServicioForm(forms.ModelForm):
    servicio = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}), label='ID del Servicio')  # Campo para ingresar el ID del servicio

    class Meta:
        model = DetalleVentaManual  # Especifica el modelo asociado
        fields = ['servicio']  # Campo incluido en el formulario

    def clean_servicio(self):
        # Método para validar que el servicio existe en la base de datos
        id_servicio = self.cleaned_data['servicio']
        try:
            return Servicio.objects.get(id=id_servicio)  # Retorna el servicio si existe
        except Servicio.DoesNotExist:
            raise ValidationError("Servicio no encontrado.")  # Error si el servicio no existe

# Formset para gestionar múltiples detalles de productos en una venta manual
DetalleVentaManualFormset = inlineformset_factory(
    VentaManual,  # Modelo padre (VentaManual)
    DetalleVentaManual,  # Modelo hijo (DetalleVentaManual)
    form=DetalleVentaManualForm,  # Formulario para los detalles
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
