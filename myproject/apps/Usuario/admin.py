from django.contrib import admin  # Importa el módulo 'admin' de Django para registrar modelos en el panel de administración.
from .models import Cliente, Empleado  # Importa los modelos 'Cliente' y 'Empleado' desde el archivo 'models' en el directorio actual.

# Register your models here.
admin.site.register(Cliente)
admin.site.register(Empleado)
