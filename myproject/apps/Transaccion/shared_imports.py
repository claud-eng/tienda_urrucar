import base64  # Importa el módulo base64 para codificación y decodificación de datos.
import calendar  # Importa el módulo 'calendar' para manejar calendarios y fechas.
import datetime  # Importa 'datetime' para trabajar con fechas y horas.
import json  # Importa el módulo json para manejar datos en formato JSON.
import locale  # Importa 'locale' para manejar configuraciones regionales, como formatos de fecha y moneda.
import logging # Importa 'logging' para crear registro de logs en un archivo.
import matplotlib.pyplot as plt  # Importa pyplot de matplotlib para crear gráficos.
import os  # Importa 'os' para interactuar con el sistema operativo.
import requests  # Importa 'requests' para realizar solicitudes HTTP.
from apps.Usuario.models import Cliente  # Importa el modelo 'Cliente' desde la aplicación 'Usuario'.
from calendar import monthrange  # Importa 'monthrange' para obtener el rango de días en un mes.
from collections import Counter  # Importa Counter para contar elementos en iterables.
from django.conf import settings  # Importa el módulo de configuración de Django.
from django.contrib import messages  # Importa 'messages' para mostrar mensajes a los usuarios en Django.
from django.contrib.auth.decorators import login_required, user_passes_test  # Importa 'login_required' y 'user_passes_test' para proteger vistas que requieren autenticación y permisos.
from django.contrib.contenttypes.models import ContentType  # Importa 'ContentType' para manejar contenido genérico en Django.
from django.contrib.staticfiles import finders  # Permite localizar archivos estáticos.
from django.core.mail import EmailMessage, send_mail  # Importa funciones para enviar correos electrónicos.
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage  # Importa 'Paginator' y excepciones para manejar la paginación.
from django.core.serializers.json import DjangoJSONEncoder  # Importa el codificador JSON específico de Django.
from django.db import models, transaction  # Importa herramientas para definir modelos y manejar transacciones en la base de datos.
from django.db.models import Q, Count, Case, When, F, Sum, DecimalField  # Importa herramientas para construir consultas complejas, expresiones condicionales y cálculos agregados.
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse  # Importa clases de respuesta y redirección HTTP.
from django.shortcuts import get_object_or_404, redirect, render  # Importa funciones de atajos para renderizar y redireccionar vistas.
from django.utils import timezone  # Importa el módulo timezone para manejar zonas horarias.
from django.utils.timezone import now, make_aware  # Importa funciones para manejar fechas y horas con conciencia de zonas horarias en Django.
from email.headerregistry import ContentTypeHeader  # Importa 'ContentTypeHeader' para manipular encabezados de correo electrónico.
from io import BytesIO  # Importa BytesIO para manejar flujos de datos en memoria.
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT  # Importa alineaciones de texto para párrafos en ReportLab.
from reportlab.lib import colors  # Importa colores de ReportLab para crear gráficos y personalizar PDFs.
from reportlab.lib.pagesizes import A4, letter  # Importa tamaños de página 'A4' y 'letter' de ReportLab.
from reportlab.lib.utils import ImageReader  # Importa ImageReader de ReportLab para manejar imágenes en PDFs.
from reportlab.pdfgen import canvas  # Importa canvas de ReportLab para generar documentos PDF.
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer, KeepTogether  # Importa elementos de ReportLab para la generación de PDFs, incluyendo tablas, imágenes, párrafos y espaciadores.
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # Importa estilos predefinidos y personalizados para texto en PDFs.
from .context_processors import formato_precio  # Importa 'formato_precio' para formatear precios en contextos de plantilla.
from .forms import * # Importa todas las funciones definidas en 'forms' del directorio actual.
from .functions import *  # Importa todas las funciones definidas en 'functions' del directorio actual.
from .models import * # Importa la función ImagenProducto para gestionar la lógica de imágenes adicionales en la galería de productos.
from django.utils import timezone  # Importa 'timezone' para manejar operaciones relacionadas con zonas horarias en Django.
from datetime import datetime, timedelta  # Importa datetime y timedelta para manejar fechas y tiempos.