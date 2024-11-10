from django.conf import settings  # Configuraciones del proyecto
from django.conf.urls.static import static  # Función para servir archivos estáticos durante el desarrollo
from django.contrib import admin  # Herramientas de administración de Django
from django.contrib.auth import views as auth_views  # Vistas de autenticación predeterminadas de Django
from django.shortcuts import render  # Función para renderizar plantillas HTML
from django.urls import include, path  # Funciones para incluir y definir rutas de URL
from apps.Usuario.forms import NewPasswordForm, ResetPasswordForm  # Formularios personalizados para restablecimiento de contraseña
from . import views  # Importación de las vistas de la aplicación actual

urlpatterns = [
    path('', lambda request: render(request, 'index.html'), name='home'),  # Página de inicio
    path('admin/', admin.site.urls),  # Administración de Django
    path('carro/', views.carro, name='carro'),  # Carrito de compras
    path('contactanos/', views.contactanos, name='contactanos'),  # Contacto
    path('enviar-correo/', views.enviar_correo_formulario, name='enviar_correo_formulario'),  # Enviar correo desde formulario
    path('login/', auth_views.LoginView.as_view(template_name='Usuario/login.html'), name='login'),  # Inicio de sesión
    path('logout/', auth_views.LogoutView.as_view(template_name='Usuario/logout.html'), name='logout'),  # Cierre de sesión
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name="Usuario/reset_password.html", form_class=ResetPasswordForm), name="password_reset"),  # Restablecimiento de contraseña
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name="Usuario/reset_password_complete.html"), name="password_reset_complete"),  # Restablecimiento de contraseña completo
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="Usuario/reset_password_confirm.html", form_class=NewPasswordForm), name="password_reset_confirm"),  # Confirmación de restablecimiento de contraseña
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name="Usuario/reset_password_done.html"), name="password_reset_done"),  # Restablecimiento de contraseña hecho
    path('preguntas_frecuentes/', views.preguntas_frecuentes, name='preguntas_frecuentes'),  # Preguntas frecuentes
    path('proceder_pago/', views.proceder_pago, name='proceder_pago'),  # Proceder con el pago
    path('producto_tienda/', views.producto_tienda, name='producto_tienda'),  # Producto en tienda
    path('regreso_pago/', views.regreso_pago, name='regreso_pago'),  # Regreso después del pago
    path('sobre_nosotros/', views.sobre_nosotros, name='sobre_nosotros'),  # Página de "sobre nosotros"
    path('tienda/', views.tienda, name='tienda'),  # Tienda de productos
    path('transaccion/', include('apps.Transaccion.urls')),  # URLs de transacciones
    path('usuario/', include('apps.Usuario.urls')),  # URLs de usuario
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)