from .functions import es_administrador, exportar_presupuesto_pdf  # Importa la función 'es_administrador' para verificar si un usuario tiene rol de administrador.
from .shared_imports import *  # Importa todas las funciones y módulos compartidos en la aplicación.

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

@user_passes_test(es_administrador, login_url='home')
def gestionar_inventario(request):
    """
    Permite al administrador gestionar el inventario de productos y servicios.
    """
    return render(request, 'Transaccion/gestionar_inventario.html')

@user_passes_test(es_administrador, login_url='home')
def gestionar_transacciones(request):
    """
    Vista para que los administradores gestionen todas las transacciones.
    """
    return render(request, 'Transaccion/gestionar_transacciones.html')

@user_passes_test(es_administrador, login_url='home')
def ver_reportes(request):
    """
    Vista para ver reportes de todas las transacciones.
    """
    return render(request, 'Transaccion/ver_reportes.html')

@user_passes_test(es_administrador, login_url='home')
def obtener_precio_producto(request):
    """
    Devuelve el precio del producto en formato JSON dado un ID de producto.
    """
    producto_id = request.GET.get('producto_id')

    try:
        producto = Producto.objects.get(id=producto_id)
        return JsonResponse({'precio': producto.precio})
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)

@user_passes_test(es_administrador, login_url='home')
def generar_presupuesto_pdf(request):
    if request.method == "POST":
        # Crear un nuevo presupuesto en la base de datos
        nuevo_presupuesto = Presupuesto.objects.create()

        # Recoger datos del formulario
        datos_presupuesto = {
            "numero_presupuesto": nuevo_presupuesto.numero_presupuesto,
            "cliente_nombre": request.POST.get("cliente_nombre"),
            "cliente_rut": request.POST.get("cliente_rut"),
            "telefono": request.POST.get("telefono"),
            "patente": request.POST.get("patente"),
            "vehiculo": request.POST.get("vehiculo"),
            "anio": request.POST.get("anio"),
            "chasis": request.POST.get("chasis"),
            "fecha_presupuesto": request.POST.get("fecha_presupuesto"),
            "fecha_validez": request.POST.get("fecha_validez"),
            "observaciones": request.POST.get("observaciones", "").strip(),
        }

        # Recoger los ítems del presupuesto (listas dinámicas)
        referencias = request.POST.getlist("referencia[]")
        tipos = request.POST.getlist("tipo[]")
        conceptos = request.POST.getlist("concepto[]")
        cantidades = request.POST.getlist("cantidad[]")
        precios_unitarios = request.POST.getlist("precio_unitario[]")
        descuentos = request.POST.getlist("descuento[]")

        # Construir la lista de ítems
        items = []
        for i in range(len(referencias)):
            items.append({
                "referencia": referencias[i],
                "tipo": tipos[i],
                "concepto": conceptos[i],
                "cantidad": int(cantidades[i]),
                "precio_unitario": float(precios_unitarios[i]),
                "descuento": float(descuentos[i])
            })

        # Generar el PDF
        pdf_buffer = exportar_presupuesto_pdf(datos_presupuesto, items)

        # Enviar el archivo como respuesta HTTP
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="presupuesto_{nuevo_presupuesto.numero_presupuesto}.pdf"'
        return response

    return render(request, "Transaccion/generar_presupuesto_pdf.html")


