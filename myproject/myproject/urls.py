from . import views  # Importación de las vistas de la aplicación actual
from .views import index  # Importa la vista index desde views.py
from apps.Usuario.forms import ResetPasswordForm, CustomPasswordResetForm, NewPasswordForm  # Formularios personalizados para restablecimiento de contraseña
from django.conf import settings  # Configuraciones del proyecto
from django.conf.urls.static import static  # Función para servir archivos estáticos durante el desarrollo
from django.contrib import admin  # Herramientas de administración de Django
from django.contrib.auth import views as auth_views  # Vistas de autenticación predeterminadas de Django
from django.shortcuts import render  # Función para renderizar plantillas HTML
from django.urls import include, path  # Funciones para incluir y definir rutas de URL

urlpatterns = [
    path('', index, name='home'),  # Página principal
    path('admin/', admin.site.urls),  # Panel de administración de Django
    path('contactanos/', views.contactanos, name='contactanos'),  # Contacto
    path('enviar-correo/', views.enviar_correo_formulario, name='enviar_correo_formulario'),  # Enviar correo desde formulario
    path('login/', auth_views.LoginView.as_view(template_name='Usuario/login.html'), name='login'),  # Inicio de sesión
    path('logout/', auth_views.LogoutView.as_view(template_name='Usuario/logout.html'), name='logout'),  # Cierre de sesión
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name="Usuario/reset_password.html", form_class=CustomPasswordResetForm, html_email_template_name='Usuario/password_reset_email.html'), name="password_reset"),  # Restablecimiento de contraseña
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name="Usuario/reset_password_done.html"), name="password_reset_done"),  # Confirmación de envío de restablecimiento
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="Usuario/reset_password_confirm.html", form_class=NewPasswordForm), name="password_reset_confirm"),  # Confirmar nueva contraseña
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name="Usuario/reset_password_complete.html"), name="password_reset_complete"),  # Restablecimiento completo
    path('preguntas_frecuentes/', views.preguntas_frecuentes, name='preguntas_frecuentes'),  # Preguntas frecuentes
    path('sobre_nosotros/', views.sobre_nosotros, name='sobre_nosotros'),  # Sobre nosotros
    path('transaccion/', include('apps.Transaccion.urls')),  # URLs de transacciones
    path('usuario/', include('apps.Usuario.urls')),  # URLs de usuario
]

if settings.DEBUG or settings.SERVE_MEDIA_IN_PRODUCTION:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)