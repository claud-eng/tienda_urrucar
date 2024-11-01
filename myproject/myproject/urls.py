"""
URL configuration for proyecto_tienda project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render
from django.contrib.auth import views as auth_views
from apps.Usuario.forms import ResetPasswordForm, NewPasswordForm
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: render(request, 'index.html'), name='home'),
    path('sobre_nosotros/', views.sobre_nosotros, name='sobre_nosotros'),
    path('carro/', views.carro, name='carro'),
    path('proceder_pago/', views.proceder_pago, name='proceder_pago'),
    path('contactanos/', views.contactanos, name='contactanos'),
    path('tienda/', views.tienda, name='tienda'),
    path('producto_tienda/', views.producto_tienda, name='producto_tienda'),
    path('regreso_pago/', views.regreso_pago, name='regreso_pago'),
    path('usuario/', include('apps.Usuario.urls')),
    path('login/', auth_views.LoginView.as_view(template_name='Usuario/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='Usuario/logout.html'), name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name="Usuario/reset_password.html", form_class=ResetPasswordForm), name="password_reset"),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name="Usuario/reset_password_done.html"), name="password_reset_done"),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="Usuario/reset_password_confirm.html", form_class=NewPasswordForm), name="password_reset_confirm"),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name="Usuario/reset_password_complete.html"), name="password_reset_complete"),
]
