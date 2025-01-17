from django.apps import AppConfig  # Importación para la configuración de la aplicación

class TransaccionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.Transaccion'

    def ready(self):
        import apps.Transaccion.signals  # Importa las señales
