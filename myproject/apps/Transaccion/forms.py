import datetime # Importa 'datetime' para trabajar con fechas y horas.
import pytz  # Para manejar zonas horarias y excepciones como cambios de horario (DST)
from apps.Usuario.forms import ClienteAnonimoForm  # Importa el formulario para clientes anónimos desde la app Usuario.
from django import forms  # Importa el módulo forms de Django para crear formularios.
from django.core.exceptions import ValidationError  # Importa ValidationError para manejar errores de validación en formularios.
from django.forms import DateTimeInput  # Importa DateTimeInput para widgets de entrada de fecha y hora.
from django.forms import inlineformset_factory  # Importa inlineformset_factory para crear formularios en línea para modelos relacionados.
from django.forms.widgets import DateInput  # Importa DateInput para widgets de entrada de fecha.
from django.utils.timezone import get_current_timezone, make_aware  # Para trabajar correctamente con fechas en zonas horarias conscientes (timezone-aware)
from .models import Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto, Servicio  # Importa los modelos Cliente, ClienteAnonimo, DetalleVentaOnline, VentaOnline, DetalleVentaManual, VentaManual, Producto, ImagenProducto y Servicio de la aplicación actual.
from datetime import datetime  # Para manejar y parsear fechas en formato estándar

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
            'nombre', 'marca', 'modelo', 'version', 'anio', 'patente',
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
        from datetime import date  # Importación local, solo dentro del método

        fecha_adquisicion = self.cleaned_data.get('fecha_adquisicion')
        if fecha_adquisicion and fecha_adquisicion > date.today():
            raise forms.ValidationError("La fecha de adquisición no puede estar en el futuro.")
        return fecha_adquisicion

    def clean(self):
        """
        Limpia y formatea los datos ingresados.
        """
        from datetime import date  # Importación local, solo dentro del método
        
        cleaned_data = super().clean()  # Llama a la limpieza predeterminada del formulario
        
        # Obtener datos
        nombre = cleaned_data.get('nombre')
        marca = cleaned_data.get('marca')
        modelo = cleaned_data.get('modelo')
        version = cleaned_data.get('version')
        anio = cleaned_data.get('anio')
        descripcion = cleaned_data.get('descripcion')

        # Si el nombre está vacío, lo construimos automáticamente
        if not nombre:
            nombre_generado = ' '.join(filter(None, [marca, modelo, version]))
            cleaned_data['nombre'] = nombre_generado
            print(f"Nombre generado automáticamente en clean(): {nombre_generado}")

        # Validar que el año sea razonable
        if anio and (anio < 1900 or anio > date.today().year + 1):
            self.add_error('anio', "El año debe estar entre 1900 y el próximo año.")

        return cleaned_data  # Retorna los datos limpios y formateados

# Imagen del producto en el Formulario
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
    fecha_creacion = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        ),
        label="Fecha de la Venta"
    )

    fecha_pago_final = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={'class': 'form-control', 'type': 'date'},
            format='%Y-%m-%d'
        ),
        label="Fecha Pago Completo"
    )

    class Meta:
        model = VentaManual
        fields = ['pago_cliente', 'precio_personalizado', 'fecha_creacion', 'fecha_pago_final']
        labels = {
            'pago_cliente': 'Monto Pagado por el Cliente',
            'precio_personalizado': 'Valor Total del Vehículo (IVA incluido)',
            'fecha_creacion': 'Fecha de la Venta',
            'fecha_pago_final': 'Fecha Pago Completo'
        }
        widgets = {
            'pago_cliente': forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_personalizado': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.is_bound:
            if self.instance and self.instance.fecha_pago_final:
                fecha_pago_str = self.instance.fecha_pago_final.strftime('%Y-%m-%d')
                self.fields['fecha_pago_final'].initial = fecha_pago_str

            if self.instance and self.instance.fecha_creacion:
                fecha_creacion_str = self.instance.fecha_creacion.strftime('%Y-%m-%d')
                self.fields['fecha_creacion'].initial = fecha_creacion_str

    def clean(self):
        cleaned_data = super().clean()
        pago_cliente = cleaned_data.get('pago_cliente') or 0
        precio_total = cleaned_data.get('precio_personalizado') or 0
        fecha_str = self.data.get('fecha_pago_final')

        fecha_final = None

        if fecha_str:
            try:
                naive_fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
                fecha_final = make_aware(datetime.combine(naive_fecha.date(), datetime.min.time()))
                print(f"Fecha interpretada correctamente: {fecha_final}")
            except ValueError:
                print("Error al interpretar la fecha.")
                self.add_error('fecha_pago_final', 'La fecha ingresada no tiene un formato válido.')

        # Validación personalizada: pago completo pero fecha no ingresada
        if pago_cliente == precio_total and not fecha_final:
            print("Error: pago cubre total, pero no se ingresó fecha de pago completo.")
            self.add_error('fecha_pago_final', 'Debes ingresar la fecha de pago completo si el monto pagado cubre el total del servicio.')

        cleaned_data['fecha_pago_final'] = fecha_final
        return cleaned_data

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

        print("Guardando instancia de VentaManual...")
        print("Fecha creación inicial:", venta.fecha_creacion)
        print("Fecha pago final inicial:", venta.fecha_pago_final)

        # Asignar fecha de pago final solo si corresponde
        if venta.pago_cliente >= venta.precio_personalizado:
            venta.fecha_pago_final = self.cleaned_data.get('fecha_pago_final')
            print("Fecha de pago final editada:", venta.fecha_pago_final)
        else:
            venta.fecha_pago_final = None
            print("Pago incompleto, fecha de pago final reseteada a None")

        print("Fecha creación final:", venta.fecha_creacion)
        print("Fecha pago final final:", venta.fecha_pago_final)

        if commit:
            venta.save()
        return venta

# Formulario de detalle de productos en venta manual
class DetalleVentaManualProductoForm(forms.ModelForm):
    nombre_producto = forms.CharField(
        label='Producto',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Escribe el nombre o patente...',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = DetalleVentaManual
        fields = []  # No incluir 'producto' directamente, lo asignamos en clean()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Mostrar el nombre completo del producto seleccionado en edición
        if self.instance and self.instance.producto:
            producto = self.instance.producto
            patente = producto.patente or "Sin patente"
            self.fields['nombre_producto'].initial = f"{producto.nombre} - {patente}"

    def clean(self):
        cleaned_data = super().clean()
        nombre_producto = cleaned_data.get('nombre_producto')
        print(f"Nombre recibido en clean(): {nombre_producto}")

        if nombre_producto:
            partes = nombre_producto.split(" - ")
            nombre = partes[0].strip()
            patente = partes[1].strip() if len(partes) > 1 else None

            print(f"Nombre: {nombre}, Patente: {patente}")

            try:
                if patente and patente.lower() != "sin patente":
                    producto = Producto.objects.get(nombre__iexact=nombre, patente__iexact=patente)
                else:
                    producto = Producto.objects.get(nombre__iexact=nombre, patente__isnull=True)
                cleaned_data['producto'] = producto
                print("Producto encontrado:", producto)
            except Producto.DoesNotExist:
                print("Producto no encontrado.")
                raise forms.ValidationError("El producto ingresado no existe o no coincide con la patente.")
        elif self.instance and self.instance.producto:
            print("Usando producto de instancia previa.")
            cleaned_data['producto'] = self.instance.producto
        else:
            print("No se ingresó un producto.")
            raise forms.ValidationError("Debe seleccionar un producto válido.")

        return cleaned_data
        
class DetalleVentaManualServicioForm(forms.ModelForm):
    nombre_servicio = forms.CharField(
        label='Servicio',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Escribe el nombre del servicio...',
            'autocomplete': 'off'
        })
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
        fields = ['precio_costo', 'marca_vehiculo', 'modelo_vehiculo', 'patente_vehiculo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Si estamos editando y hay un servicio asociado, mostrar su nombre por defecto
        if self.instance and self.instance.servicio:
            self.fields['nombre_servicio'].initial = self.instance.servicio.nombre

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre_servicio')

        if nombre:
            try:
                servicio = Servicio.objects.get(nombre__iexact=nombre)
                cleaned_data['servicio'] = servicio
            except Servicio.DoesNotExist:
                raise ValidationError("El servicio ingresado no existe.")
        elif self.instance and self.instance.servicio:
            # Si no se ingresó uno nuevo, pero existe ya uno asociado (modo edición)
            cleaned_data['servicio'] = self.instance.servicio
        else:
            raise ValidationError("Debe seleccionar un servicio válido.")

        return cleaned_data

# Formset para gestionar múltiples detalles en una venta online
DetalleVentaOnlineFormset = inlineformset_factory(
    VentaOnline,  # Modelo padre
    DetalleVentaOnline,  # Modelo hijo
    form=DetalleVentaOnlineForm,
    fields=('producto', 'cantidad', 'precio', 'estado_reserva'),
    extra=1,  # Número de formularios adicionales
    can_delete=True,  # Permitir eliminar ítems
)


