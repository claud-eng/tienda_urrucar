import re  # Importar el módulo 're' (expresiones regulares), que se utiliza para realizar validaciones basadas en patrones.
from datetime import date  # Importar el módulo 'date' desde 'datetime', que se usa para manipular fechas.
from django import forms  # Importar la clase 'forms' de Django, que se utiliza para crear formularios.
from django.contrib.auth import password_validation  # Importar herramientas de validación de contraseñas proporcionadas por Django.
from django.contrib.auth.forms import (
    AuthenticationForm,  # Formulario de autenticación de Django.
    PasswordChangeForm,  # Formulario para cambiar la contraseña del usuario.
    PasswordResetForm,  # Formulario para solicitar el restablecimiento de contraseña.
    SetPasswordForm,  # Formulario para establecer una nueva contraseña después de un restablecimiento.
    UserChangeForm,  # Formulario para actualizar datos de usuario.
    UserCreationForm  # Formulario para crear un nuevo usuario.
)
from django.contrib.auth.hashers import make_password  # Importar la función para encriptar contraseñas de Django.
from django.contrib.auth.models import User  # Importar el modelo 'User' de Django, que se utiliza para gestionar usuarios.
from django.contrib.auth.tokens import default_token_generator  # Generador de tokens que se usa para verificar enlaces de restablecimiento de contraseña.
from django.core.exceptions import ValidationError  # Importar la excepción 'ValidationError' para manejar errores de validación.
from django.core.mail import send_mail  # Función para enviar correos electrónicos desde Django.
from django.template.loader import render_to_string  # Función para renderizar plantillas HTML en formato de cadena de texto.
from django.utils.encoding import force_bytes  # Codifica datos en bytes (usado para generar tokens seguros).
from django.utils.html import strip_tags  # Elimina etiquetas HTML de una cadena, dejando solo el texto plano.
from django.utils.http import urlsafe_base64_encode  # Codifica datos en base64 de forma segura para URLs.
from apps.Usuario.models import Cliente, ClienteAnonimo, Empleado  # Importar los modelos 'Cliente' y 'Empleado' desde la aplicación 'Usuario'.

def validate_username(value):
    """
    Valida que 'value' sea un correo electrónico con el dominio @urrucar.cl.
    Lanza una excepción forms.ValidationError si no cumple con el formato esperado.
    """
    if not value.endswith('@urrucar.cl'):
        # Si el correo no termina en el dominio especificado, lanza un error de validación.
        raise forms.ValidationError('El nombre de usuario debe ser un correo electrónico con el dominio @urrucar.cl.')

def validate_rut_chileno(value):
    """
    Valida que 'value' sea un Rut chileno válido con formato X.XXX.XXX-X o XX.XXX.XXX-X.
    Convierte cualquier letra 'K' en minúscula a mayúscula antes de la validación.
    Lanza una excepción ValidationError si el formato no es válido.
    """
    rut = value.upper()  # Convertir a mayúsculas para manejar 'K' en minúscula
    rut_formato_valido = re.match(r'^[1-9]\d*\.\d{3}\.\d{3}-[0-9K]$', rut)

    if not rut_formato_valido:
        # Si el formato no coincide con el esperado, lanza un error de validación.
        raise ValidationError('El Rut no es válido. El formato debe ser X.XXX.XXX-X o XX.XXX.XXX-X (donde X representa dígitos y el último carácter puede ser un dígito o "K").')

class ClienteForm(forms.ModelForm):
    # Definición de un formulario para crear clientes.

    # Campo personalizado para el nombre de usuario (correo electrónico)
    username = forms.EmailField(
        max_length=150,
        required=True,
        label='Usuario (Correo Electrónico)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@gmail.com'}),
        # No incluir la validación de validate_username
    )

    def clean_username(self):
        # Validación adicional: asegura que el nombre de usuario no esté en uso.
        username = self.cleaned_data['username']
    
        # Verificar si el dominio es "@urrucar.cl"
        if username.endswith('@urrucar.cl'):
            raise forms.ValidationError('No se permite registrar un cliente con el dominio @urrucar.cl.')

        # Verificar si el nombre de usuario ya está en uso.
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('El nombre de usuario ya está en uso.')
    
        return username

    # Campo para la contraseña con validaciones
    password = forms.CharField(
        max_length=128,
        required=True,
        label='Contraseña',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña', 'type': 'password'}),
        validators=[
            password_validation.validate_password,
        ],
    )

    # Campos personalizados para el nombre y apellido
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alejandra'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Primer Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Torres'}),
    )

    second_last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Segundo Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Herrera'}),
    )
    fecha_nacimiento = forms.DateField(
        required=True,
        label='Fecha de Nacimiento',
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def clean_fecha_nacimiento(self):
        # Validación adicional para verificar que el usuario tenga al menos 18 años
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')

        if fecha_nacimiento:
            edad = (date.today() - fecha_nacimiento).days // 365  # Calcula la edad en años
            if edad < 18:
                raise ValidationError('Debes ser mayor de 18 años para registrarte.')

        return fecha_nacimiento
    
    numero_telefono = forms.CharField(
        max_length=15,
        required=True,
        label='Número de Teléfono',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'}),
    )

    class Meta:
        # Define el modelo de base y los campos que aparecerán en el formulario
        model = Cliente
        fields = ['username', 'password', 'first_name', 'last_name', 'second_last_name', 'fecha_nacimiento', 'numero_telefono',]

    def save(self, commit=True):
        # Crear o actualizar el usuario (auth_user)
        user, created = User.objects.get_or_create(username=self.cleaned_data['username'])
        user.email = self.cleaned_data['username']  # Actualiza el campo email con el valor del username
        user.first_name = self.cleaned_data['first_name'].capitalize()  # Transforma la primera letra en mayúscula
        user.last_name = self.cleaned_data['last_name'].capitalize()  # Transforma la primera letra en mayúscula
        # Hashear la contraseña antes de guardarla
        user.password = make_password(self.cleaned_data['password'])  # Hashear la contraseña

        if commit:
            user.save()

        # Crear o actualizar el cliente
        cliente = super(ClienteForm, self).save(commit=False)
        cliente.user = user
        cliente.second_last_name = self.cleaned_data['second_last_name'].capitalize()  # Transforma la primera letra en mayúscula

        if commit:
            cliente.save()

        return cliente
    
class EditarClienteForm(forms.ModelForm):
    # Campos y configuraciones para el formulario de edición de clientes (excluye contraseña)

    # Campo personalizado para el nombre de usuario (correo electrónico)
    username = forms.EmailField(
        max_length=150,
        required=True,
        label='Usuario (Correo Electrónico)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@gmail.com'}),
        # No incluir la validación de validate_username
    )

    def clean_username(self):
        # Validación adicional: asegura que el nombre de usuario no esté en uso,
        # solo si el valor ha cambiado
        username = self.cleaned_data['username']
        if username != self.instance.user.username:
            # Verificar si el dominio es "@urrucar.cl"
            if username.endswith('@urrucar.cl'):
                raise forms.ValidationError('No se permite registrar un cliente con el dominio @urrucar.cl.')

            # Verificar si el nombre de usuario ya está en uso.
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('El nombre de usuario ya está en uso.')

        return username
    
    # Campos personalizados para el nombre y apellido
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alejandra'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Primer Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Torres'}),
    )

    second_last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Segundo Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Herrera'}),
    )
    fecha_nacimiento = forms.DateField(
        required=True,
        label='Fecha de Nacimiento',
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')

        if fecha_nacimiento:
            edad = (date.today() - fecha_nacimiento).days // 365  # Calcula la edad en años
            if edad < 18:
                raise ValidationError('Debes ser mayor de 18 años para registrarte.')

        return fecha_nacimiento
    
    numero_telefono = forms.CharField(
        max_length=15,
        required=True,
        label='Número de Teléfono',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'}),
    )

    class Meta:
        model = Cliente
        fields = ['username', 'first_name', 'last_name', 'second_last_name', 'fecha_nacimiento', 'numero_telefono',]

    def save(self, commit=True):
        # Obtener la instancia del cliente actual
        cliente = super(EditarClienteForm, self).save(commit=False)

        # Obtener el usuario asociado al cliente actual
        user = cliente.user

        # Actualizar los campos del usuario (correo electrónico, nombre, apellido, etc.)
        user.username = self.cleaned_data['username']
        user.first_name = self.cleaned_data['first_name'].capitalize()  # Transforma la primera letra en mayúscula
        user.last_name = self.cleaned_data['last_name'].capitalize()  # Transforma la primera letra en mayúscula

        if commit:
            user.save()  # Guardar los cambios en el usuario

        cliente.second_last_name = self.cleaned_data['second_last_name'].capitalize()  # Transforma la primera letra en mayúscula

        if commit:
            cliente.save()  # Guardar los cambios en el cliente

        return cliente

class CustomClienteForm(forms.ModelForm):
    
    # Campo personalizado para el nombre de usuario (correo electrónico)
    username = forms.EmailField(
        max_length=150,
        required=True,
        label='Usuario (Correo Electrónico)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@gmail.com'}),
    )

    def clean_username(self):
        # Validación adicional: asegura que el nombre de usuario no esté en uso,
        # solo si el valor ha cambiado
        username = self.cleaned_data['username']
        if username != self.instance.user.username:
            # Verificar si el dominio es "@urrucar.cl"
            if username.endswith('@urrucar.cl'):
                raise forms.ValidationError('No se permite registrar un cliente con el dominio @urrucar.cl.')

            # Verificar si el nombre de usuario ya está en uso.
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError('El nombre de usuario ya está en uso.')

        return username
    
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    second_last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    fecha_nacimiento = forms.DateField(
        required=True,
        label='Fecha de Nacimiento',
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')

        if fecha_nacimiento:
            edad = (date.today() - fecha_nacimiento).days // 365  # Calcula la edad en años
            if edad < 18:
                raise ValidationError('Debes ser mayor de 18 años para registrarte.')

        return fecha_nacimiento
    
    numero_telefono = forms.CharField(max_length=15, widget=forms.TextInput(attrs={'class': 'form-control'}))

    def clean_first_name(self):
        # Asegurar que la primera letra sea mayúscula y el resto minúscula
        first_name = self.cleaned_data['first_name'].capitalize()
        return first_name

    def clean_last_name(self):
        # Asegurar que la primera letra sea mayúscula y el resto minúscula
        last_name = self.cleaned_data['last_name'].capitalize()
        return last_name

    def clean_second_last_name(self):
        # Asegurar que la primera letra sea mayúscula y el resto minúscula
        second_last_name = self.cleaned_data['second_last_name'].capitalize()
        return second_last_name
    
    class Meta:
        model = Cliente
        fields = ['username', 'first_name', 'last_name', 'second_last_name', 'fecha_nacimiento', 'numero_telefono']

class CambiarContraseñaUsuarioForm(PasswordChangeForm):
    class Meta:
        model = User  # Utiliza el modelo User de Django
        fields = ('old_password', 'new_password1', 'new_password2')  # Campos para cambiar la contraseña

# Formulario para cliente anónimo
class ClienteAnonimoForm(forms.ModelForm):
    class Meta:
        model = ClienteAnonimo
        fields = ['nombre', 'apellido', 'email', 'numero_telefono', 'rut']
        labels = {
            'rut': 'RUT',
        }
        widgets = {
            'rut': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingresar con puntos y guión: XX.XXX.XXX-X'
            }),
        }

class EmpleadoForm(forms.ModelForm):
    # Definición de un formulario para crear empleados.

    # Campo personalizado para el nombre de usuario (correo electrónico)
    username = forms.EmailField(
        max_length=150,
        required=True,
        label='Usuario (Correo Electrónico)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@urrucar.cl'}),
        validators=[validate_username],  # Validación personalizada
    )

    def clean_username(self):
        # Validación adicional: Verificar si el nombre de usuario ya existe
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError('El nombre de usuario ya está en uso.')
        return username

    # Campo para la contraseña con validaciones
    password = forms.CharField(
        max_length=128,
        required=True,
        label='Contraseña',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña', 'type': 'password'}),
        validators=[
            password_validation.validate_password,
        ],
    )

    # Campos personalizados para el nombre y apellido
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alejandra'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Primer Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Torres'}),
    )

    rut = forms.CharField(
        max_length=12,
        required=True,
        label='RUT',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingresar con puntos y guión: XX.XXX.XXX-X'}),
        validators=[validate_rut_chileno],  # Aplicar la validación personalizada de RUT
    )
    def clean_rut(self):
        # Validación adicional: Convierte la letra 'K' (si existe) a mayúscula antes de guardar
        rut = self.cleaned_data['rut']
        rut = rut.upper()
        return rut
    
    second_last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Segundo Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Herrera'}),
    )
    fecha_nacimiento = forms.DateField(
        required=True,
        label='Fecha de Nacimiento',
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')

        if fecha_nacimiento:
            edad = (date.today() - fecha_nacimiento).days // 365  # Calcula la edad en años
            if edad < 18:
                raise ValidationError('Debes ser mayor de 18 años para registrarte.')

        return fecha_nacimiento
    
    numero_telefono = forms.CharField(
        max_length=15,
        required=True,
        label='Número de Teléfono',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'}),
    )

    # Campo para el rol con opciones limitadas
    ROL_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Vendedor', 'Vendedor'),
    ]
    rol = forms.ChoiceField(choices=ROL_CHOICES, label='Rol', widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Empleado
        fields = ['username', 'password', 'rut', 'first_name', 'last_name', 'second_last_name', 'fecha_nacimiento', 'numero_telefono', 'rol',]

    def save(self, commit=True):
        # Crear o actualizar el usuario (auth_user)
        user, created = User.objects.get_or_create(username=self.cleaned_data['username'])
        user.first_name = self.cleaned_data['first_name'].capitalize()  # Transforma la primera letra en mayúscula
        user.last_name = self.cleaned_data['last_name'].capitalize()  # Transforma la primera letra en mayúscula

        # Hashear la contraseña antes de guardarla
        user.password = make_password(self.cleaned_data['password'])  # Hashear la contraseña

        if commit:
            user.save()

        # Crear o actualizar el empleado
        empleado = super(EmpleadoForm, self).save(commit=False)
        empleado.user = user
        empleado.second_last_name = self.cleaned_data['second_last_name'].capitalize()  # Transforma la primera letra en mayúscula
        if commit:
            empleado.save()

        return empleado

class EditarEmpleadoForm(forms.ModelForm):
    # Campos y configuraciones para el formulario de edición de empleados
    # Excluye el campo de contraseña y otras configuraciones relacionadas con la contraseña

    # Campo personalizado para el nombre de usuario (correo electrónico)
    username = forms.EmailField(
        max_length=150,
        required=True,
        label='Usuario (Correo Electrónico)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@urrucar.cl'}),
        validators=[validate_username],  # Validación personalizada
    )

    # Campos personalizados para el nombre y apellido
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Alejandra'}),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label='Primer Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Torres'}),
    )

    rut = forms.CharField(
        max_length=12,
        required=True,
        label='RUT',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingresar con puntos y guión: XX.XXX.XXX-X'}),
        validators=[validate_rut_chileno],  # Aplicar la validación personalizada de RUT
    )

    def clean_rut(self):
        # Validación adicional: Convierte la letra 'K' (si existe) a mayúscula antes de guardar
        rut = self.cleaned_data['rut']
        rut = rut.upper()
        return rut
    
    second_last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Segundo Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Herrera'}),
    )
    fecha_nacimiento = forms.DateField(
        required=True,
        label='Fecha de Nacimiento',
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'date'}),
    )

    def clean_fecha_nacimiento(self):
        fecha_nacimiento = self.cleaned_data.get('fecha_nacimiento')

        if fecha_nacimiento:
            edad = (date.today() - fecha_nacimiento).days // 365  # Calcula la edad en años
            if edad < 18:
                raise ValidationError('Debes ser mayor de 18 años para registrarte.')

        return fecha_nacimiento
    
    numero_telefono = forms.CharField(
        max_length=15,
        required=True,
        label='Número de Teléfono',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+56912345678'}),
    )

    # Campo para el rol con opciones limitadas
    ROL_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Vendedor', 'Vendedor'),
    ]
    rol = forms.ChoiceField(choices=ROL_CHOICES, label='Rol', widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Empleado
        fields = ['username', 'rut', 'first_name', 'last_name', 'second_last_name', 'fecha_nacimiento', 'numero_telefono', 'rol',]

    def save(self, commit=True):
        # Crear o actualizar el usuario (auth_user)
        user, created = User.objects.get_or_create(username=self.cleaned_data['username'])
        user.first_name = self.cleaned_data['first_name'].capitalize()  # Transforma la primera letra en mayúscula
        user.last_name = self.cleaned_data['last_name'].capitalize()  # Transforma la primera letra en mayúscula

        if commit:
            user.save()

        # Crear o actualizar el empleado
        empleado = super(EditarEmpleadoForm, self).save(commit=False)
        empleado.user = user
        empleado.second_last_name = self.cleaned_data['second_last_name'].capitalize()  # Transforma la primera letra en mayúscula
        if commit:
            empleado.save()

        return empleado

# Formulario estándar para restablecer la contraseña
class ResetPasswordForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        # Inicializa el formulario de restablecimiento de contraseña
        super(ResetPasswordForm, self).__init__(*args, **kwargs)

    email = forms.EmailField(
        max_length=150,
        required=True,
        label='Usuario (Correo Electrónico)',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@gmail.com'}),
    )

# Formulario personalizado que envía un HTML específico para restablecer la contraseña
class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        max_length=150,
        required=True,
        label='Correo Electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@gmail.com'}),
    )

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        html_message = render_to_string(html_email_template_name, context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject='Restablecimiento de contraseña',
            message=plain_message,
            from_email=from_email,
            recipient_list=[to_email],
            html_message=html_message
        )

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None, extra_email_context=None):

        email = self.cleaned_data["email"]
        for user in User.objects.filter(email=email):
            context = {
                'email': user.email,
                'domain': domain_override or request.get_host(),
                'site_name': 'Urrucar Automotriz',
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': 'https' if use_https else 'http',
            }
            if extra_email_context:
                context.update(extra_email_context)

            self.send_mail(subject_template_name, email_template_name,
                           context, from_email, user.email,
                           html_email_template_name='Usuario/password_reset_email.html')
            
class NewPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        # Inicializa el formulario de nueva contraseña
        super(NewPasswordForm, self).__init__(*args, **kwargs)

    new_password1 = forms.CharField(
        max_length=128,
        required=True,
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'type': 'password', 'autocomplete': 'new-password'}),
    )

    new_password2 = forms.CharField(
        max_length=128,
        required=True,
        label='Confirmar Nueva Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'type': 'password', 'autocomplete': 'new-password'}),
    )
