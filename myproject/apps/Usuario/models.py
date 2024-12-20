from django.db import models  # Importa modelos de Django para definir estructuras de base de datos
from django.db.models.signals import post_delete  # Importa la señal para acciones después de eliminar un registro
from django.contrib.auth.models import User  # Importa el modelo User para la relación con Cliente y Empleado
from django.dispatch import receiver  # Importa el receptor de señales para realizar acciones al recibir una señal

# Modelo para almacenar información del cliente
class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Relación uno a uno con el usuario
    rut = models.CharField(max_length=12, default='')  # Identificación RUT del cliente
    second_last_name = models.CharField(max_length=150, default='')  # Segundo apellido del cliente
    fecha_nacimiento = models.DateField()  # Fecha de nacimiento del cliente
    numero_telefono = models.CharField(max_length=15, default='')  # Número de teléfono del cliente

    def __str__(self):
        return self.user.username  # Retorna el nombre de usuario como representación en cadena
    
# Modelo para usuarios no registrados
class ClienteAnonimo(models.Model):
    nombre = models.CharField(max_length=150) # Nombre del cliente anónimo
    apellido = models.CharField(max_length=150) # Apellido del cliente anónimo
    email = models.EmailField() # Correo del cliente anónimo
    numero_telefono = models.CharField(max_length=15, blank=True, null=True) # Número de teléfono del cliente anónimo
    session_key = models.CharField(max_length=255, unique=True)  # Identificador único basado en la sesión

    def __str__(self):
        return self.email # Retorna el correo del usuario anónimo como representación en cadena

# Modelo para almacenar información del empleado
class Empleado(models.Model):
    ROLE_CHOICES = [  # Opciones de rol para el empleado
        ('Administrador', 'Administrador'),  # Rol de Administrador
        ('Vendedor', 'Vendedor'),  # Rol de Vendedor
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Relación uno a uno con el usuario
    rut = models.CharField(max_length=12, default='')  # Identificación RUT del empleado
    second_last_name = models.CharField(max_length=150, default='')  # Segundo apellido del empleado
    fecha_nacimiento = models.DateField()  # Fecha de nacimiento del empleado
    numero_telefono = models.CharField(max_length=15, default='')  # Número de teléfono del empleado
    rol = models.CharField(max_length=50, choices=ROLE_CHOICES)  # Rol del empleado (Administrador o Vendedor)

    def __str__(self):
        return self.user.username  # Retorna el nombre de usuario como representación en cadena

# Señal para eliminar el usuario cuando se elimina un cliente
@receiver(post_delete, sender=Cliente)
def eliminar_usuario_cliente(sender, instance, **kwargs):
    # Si el cliente tiene un usuario asociado, lo elimina
    if instance.user:
        instance.user.delete()

# Señal para eliminar el usuario cuando se elimina un empleado
@receiver(post_delete, sender=Empleado)
def eliminar_usuario_empleado(sender, instance, **kwargs):
    # Si el empleado tiene un usuario asociado, lo elimina
    if instance.user:
        instance.user.delete()
