from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rut = models.CharField(max_length=12, default='')
    second_last_name = models.CharField(max_length=150, default='')
    fecha_nacimiento = models.DateField()
    numero_telefono = models.CharField(max_length=15, default='')

    def __str__(self):
        return self.user.username

class Empleado(models.Model):
    ROLE_CHOICES = [
        ('Administrador', 'Administrador'),
        ('Vendedor', 'Vendedor'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rut = models.CharField(max_length=12, default='')
    second_last_name = models.CharField(max_length=150, default='')
    fecha_nacimiento = models.DateField()
    numero_telefono = models.CharField(max_length=15, default='')
    rol = models.CharField(max_length=50, choices=ROLE_CHOICES)

    def __str__(self):
        return self.user.username

@receiver(post_delete, sender=Cliente)
def eliminar_usuario_cliente(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()

@receiver(post_delete, sender=Empleado)
def eliminar_usuario_empleado(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()
