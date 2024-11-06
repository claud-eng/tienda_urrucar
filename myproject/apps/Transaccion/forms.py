from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory
from .models import OrdenDeVenta, DetalleOrdenVenta, Cliente, Producto, Servicio

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'marca', 'categoria', 'descripcion', 'precio', 'cantidad_stock', 'imagen']
        # Define los widgets y atributos de clase según tus necesidades

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        marca = cleaned_data.get('marca')
        categoria = cleaned_data.get('categoria')
        descripcion = cleaned_data.get('descripcion')

        if nombre:
            cleaned_data['nombre'] = nombre.capitalize()
        if marca:
            cleaned_data['marca'] = marca.capitalize()
        if marca:
            cleaned_data['categoria'] = categoria.capitalize()
        if descripcion:
            cleaned_data['descripcion'] = descripcion.capitalize()

        return cleaned_data

class ServicioForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'precio']
        # Define los widgets y atributos de clase según tus necesidades

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        descripcion = cleaned_data.get('descripcion')

        if nombre:
            cleaned_data['nombre'] = nombre.capitalize()
        if descripcion:
            cleaned_data['descripcion'] = descripcion.capitalize()

        return cleaned_data
    
class OrdenDeVentaForm(forms.ModelForm):
    cliente = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}), label='ID del Cliente')

    class Meta:
        model = OrdenDeVenta
        fields = ['cliente', 'pago_cliente']
        widgets = {
            'pago_cliente': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_cliente(self):
        id_cliente = self.cleaned_data['cliente']
        try:
            return Cliente.objects.get(id=id_cliente)
        except Cliente.DoesNotExist:
            raise ValidationError("Cliente no encontrado.")

class DetalleOrdenVentaForm(forms.ModelForm):
    producto = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}), label='ID del Producto')

    class Meta:
        model = DetalleOrdenVenta
        fields = ['producto', 'cantidad']
        widgets = {
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_producto(self):
        id_producto = self.cleaned_data['producto']
        try:
            return Producto.objects.get(id=id_producto)
        except Producto.DoesNotExist:
            raise ValidationError("Producto no encontrado.")

class DetalleOrdenVentaServicioForm(forms.ModelForm):
    servicio = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}), label='ID del Servicio')

    class Meta:
        model = DetalleOrdenVenta
        fields = ['servicio']

    def clean_servicio(self):
        id_servicio = self.cleaned_data['servicio']
        try:
            return Servicio.objects.get(id=id_servicio)
        except Servicio.DoesNotExist:
            raise ValidationError("Servicio no encontrado.")

# Formset para múltiples DetalleOrdenVenta
DetalleOrdenVentaFormset = inlineformset_factory(
    OrdenDeVenta,
    DetalleOrdenVenta,
    form=DetalleOrdenVentaForm,
    fields=('producto', 'cantidad',),
    extra=1,
    can_delete=True
)

# Formset para múltiples DetalleOrdenVenta de Servicio
DetalleOrdenVentaServicioFormset = inlineformset_factory(
    OrdenDeVenta,
    DetalleOrdenVenta,
    form=DetalleOrdenVentaServicioForm,
    fields=('servicio',),
    extra=1,
    can_delete=True
)