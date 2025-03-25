from .functions import es_administrador, exportar_presupuesto_pdf, exportar_informe_inspeccion_pdf  # Importa la función 'es_administrador' para verificar si un usuario tiene rol de administrador.
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
    """
    Genera un nuevo presupuesto en formato PDF.
    """
    if request.method == "POST":
        # Crear un nuevo presupuesto en la base de datos
        nuevo_presupuesto = Presupuesto.objects.create()

        # Recoger datos del formulario
        datos_presupuesto = {
            "numero_presupuesto": nuevo_presupuesto.numero_presupuesto,
            "nombre_cliente": request.POST.get("nombre_cliente") or "",
            "rut_cliente": request.POST.get("rut_cliente") or "",
            "telefono": request.POST.get("telefono") or "",
            "patente": request.POST.get("patente") or "",
            "vehiculo": request.POST.get("vehiculo") or "",
            "anio": request.POST.get("anio") or "",
            "chasis": request.POST.get("chasis") or "",
            "fecha_presupuesto": request.POST.get("fecha_presupuesto") or "",
            "fecha_validez": request.POST.get("fecha_validez") or "",
            "observaciones": request.POST.get("observaciones", "").strip()
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

@user_passes_test(es_administrador, login_url='home')
def generar_informe_inspeccion_pdf(request):
    """
    Genera un nuevo informe de inspección en formato PDF.
    """
    # SOLO cuando es un GET, preparar la tabla para el formulario HTML
    secciones_inspeccion = [
        {
            "titulo": "1. SISTEMA DE SUSPENSIÓN, TREN DELANTERO Y FRENOS",
            "items": [
                "Revisión visual neumáticos (desgaste parejo, roturas, grietas, clavos)",
                "Revisión de cazoletas",
                "Revisión de espirales",
                "Revisión amortiguadores (Revisión humedad, Revisión rebote)",
                "Revisión discos de freno",
                "Revisión frenos desgaste de pastillas",
                "Revisión pasadores de caliper de freno delanteros",
                "Revisión pasadores de caliper de freno traseros",
                "Revisión fuga líquido freno por niples",
                "Revisión fuga líquido freno por flexibles",
                "Revisión cable sensor ABS",
                "Revisión sensores cables de sensores de pastillas delanteros",
                "Revisión sensores cables de sensores de pastillas traseros",
                "Revisión fuelles de caja de dirección",
                "Revisión fuelles de homocinética",
                "Revisión bujes de bandejas",
                "Revisión rotulas de bandejas",
                "Revisión bandejas",
                "Revisión terminales de dirección",
                "Revisión zumbido en rodamientos de masa delanteros",
                "Revisión zumbido en rodamientos de masa traseros",
                "Revisión paquetes de resorte (no estén quebrados ni tengan bujes rotos)",
                "Revisión barras de torsión que no hayan fugas de aceite en diferencial trasero",
                "Revisión crucetas de cardan",
                "Revisión cardan (mover cardan para ver que haya juego en el muñón)",
                "Revisión cardan corto cuando tiene transfer (mover cardan que no haya juego)",
            ]
        },
        {
            "titulo": "2. MOTOR",
            "items": [
                "Revisión ruidos de golpeteo de motor",
                "Revisión ruidos golpe valvular o taquis",
                "Revisión ruidos de chillidos en correas",
                "Revisión ruidos de bomba de agua",
                "Revisión ruidos en bomba de dirección hidráulica",
                "Revisión ruidos rodamientos varios",
                "Revisión ruidos en rodamiento de alternador",
                "Revisión ruidos de fuga de escape",
                "Revisión ruidos de fuga de aire",
                "Revisión ruidos en caja de cambios",
                "Revisión ruido rodamiento empuje",
                "Revisión fugas de agua en mangueras de radiador",
                "Revisión fugas de agua radiador calefacción",
                "Revisión fugas mangueras de agua",
                "Revisión fugas y oxido en tapa termostato",
                "Revisión fugas y oxido en carcaza termostato",
                "Revisión fugas y oxido en bomba de agua",
                "Revisión fuga y oxido en tapa depósito radiador",
                "Revisión fuga y oxido en tapa depósito agua",
                "Revisión fuga en mangueras de calefacción",
                "Revisión fugas y oxido en radiador",
                "Revisión fugas y oxido en sellos de agua de motor",
                "Revisión fugas de aceite en tapa de válvulas",
                "Revisión fugas de aceite en empaquetadura de culatas",
                "Revisión fugas aceite en retén de distribución",
                "Revisión fugas aceite en carter",
                "Revisión fugas aceite en retén de cola caja de cambios",
                "Revisión fugas aceite en diferencial",
                "Revisión fugas aceite en filtro de aceite",
                "Revisión tapa de depósito de agua que no tenga aceite",
                "Revisión tapa de aceite libre de agua",
                "Revisión fuga de líquido de frenos",
                "Revisión de fuga de líquido hidráulico",
                "Revisión de fuga de líquido limpia parabrisas",
                "Revisión correa AC",
                "Revisión de correa alternador",
                "Revisión de correa de dirección",
                "Revisión ruidos en distribución, si existe información de fecha Km",
                "Revisión nivel de aceite",
                "Revisión nivel de coolant",
                "Revisión nivel de líquido de frenos",
                "Revisión de nivel líquido hidráulico",
                "Revisión escape (que no tire humo negro, blanco o azul)",
                "Revisión fugas de escape",
                "Revisión soporte motor visual y con presión",
                "Revisión de golpeteo en inyectores en caso de ser diésel",
                "Revisión empaquetaduras (sin manipulación, motor sin abrir, Revisión juntas y pegamentos)",
                "Revisión posibles ruidos o anomalías en compresor de AC",
            ]
        },
        {
            "titulo": "3. REVISIÓN EN RUTA",
            "items": [
                "Revisión Alineación",
                "Revisión Balanceo",
                "Revisión caja de cambios (que pasen sin problemas, sin asperezas ni ruidos)",
                "Revisión embrague que corte bien, que no tenga ruidos de pedal o rodamiento ni patine",
                "Revisión ruidos de dirección (bomba, homocinética, terminales dirección, rodamientos de masa)",
                "Revisión frenos (chillidos, raspado, crujido de balatas, zumbido al frenar, vibración al frenar, pedal esponjoso o largo)",
                "Revisión temperatura motor (indicador en la mitad o sin luces de alta encendidas)",
                "Revisión indicadores tablero (odómetro, velocímetro, testigos varios, temperatura, presión de aceite, batería)",
                "Revisión velocidad crucero",
                "Revisión motor (pérdida de potencia, ruidos de golpeteo, tirones, se chupa o tiene explosiones)",
                "Revisión humo en caso que sea notorio",
                "Revisión ruidos de escape (cascabeleo catalítico, escape suelto o soporte)",
                "Revisión sonidos de carrocería",
                "Revisión ruidos de suspensión y tren delantero",
                "Revisión cremallera de dirección (que no tenga juego ni crujido)",
                "Revisión ruidos de correas",
                "Revisión eficacia frenos (ABS o convencional)",
                "Revisión cambios automáticos (que pasen de acuerdo a la velocidad, que no de tirones al salir o bajar marchas)",
                "Revisión funcionamiento de 4WD (manual y automática)",
                "Revisión ruidos de crucetas, diferencial o cardan",
                "Revisión funcionamiento de turbo (que cargue adecuadamente, que no tenga ruido ni sople)",
            ]
        },
        {
            "titulo": "4. EXTERIOR",
            "items": [
                "Revisión latas",
                "Revisión estado pintura",
                "Revisión choques",
                "Revisión parabrisas",
                "Revisión apertura y cierre cuadratura puertas",
                "Revisión espejos laterales",
                "Revisión dado de seguridad",
                "Revisión vidrios de puertas",
                "Revisión VIN visual en chasis",
                "Revisión Molduras e insignias",
                "Revisión Ópticos y focos",
                "Revisión Antena eléctrica",
                "Revisión Alarma",
            ]
        },
        {
            "titulo": "5. GENERAL",
            "items": [
                "Papeles al día"
            ]
        },
        {
            "titulo": "6. INTERIOR",
            "items": [
                "Revisión estado llaves (controles y apertura)",
                "Revisión arranque motor",
                "Revisión luces y testigos tablero apagados",
                "Revisión vibración ralentí (posibles bujías, bobina, cables)",
                "Revisión estado plásticos air bag (sin cortes ni roturas)",
                "Revisión dirección (a tope, ruidos, vibración o golpes)",
                "Revisión ruidos de embrague",
                "Revisión dureza en pedal de embrague",
                "Revisión de capota eléctrica en caso de existir (cabrio)",
                "Revisión sunroof",
                "Revisión corte de embrague (muy arriba o muy abajo)",
                "Revisión pedal de freno (que no se vaya a fondo)",
                "Revisión pedal de aceleración (que acelere sin fallar)",
                "Revisión Kilometraje",
                "Revisión bocina",
                "Revisión cierre centralizado",
                "Revisión alza vidrios eléctricos",
                "Revisión espejos eléctricos laterales",
                "Revisión señalizadores",
                "Revisión luces",
                "Revisión comandos calefacción y AC",
                "Revisión de controles al volante",
                "Revisión sapitos de agua delanteros y traseros",
                "Revisión limpia parabrisas",
                "Revisión radio (Revisión USB, aux, cd y emisoras)",
                "Revisión calefacción (que caliente)",
                "Revisión enfriamiento AC",
                "Revisión estado general interior",
                "Revisión tapices",
                "Revisión eficacia freno mano (4 a 6 dientes)",
                "Revisión sensores acercamiento",
                "Revisión cámara de retroceso",
                "Revisión correderas asientos (manual o eléctrico)",
                "Revisión cinturones seguridad",
                "Revisión neumático repuesto",
                "Revisión herramientas auto",
                "Revisión botiquín",
            ]
        },
        {
            "titulo": "7. SISTEMA ELÉCTRICO Y ELECTRÓNICO",
            "items": [
                "Scanner (Revisión códigos de falla, almacenados, chequeo general a sistemas)",
                "Revisión carga batería"
            ]
        }
    ]

    if request.method == "POST":
        # Crear una nueva instancia de inspección para generar el código interno automáticamente
        nueva_inspeccion = InformeInspeccion.objects.create()

        # Obtener las imágenes cargadas (pueden ser múltiples)
        imagenes = request.FILES.getlist("imagenes")

        # Recoger los datos del formulario
        datos_inspeccion = {
            "fecha": request.POST.get("fecha") or "",
            "nombre_inspector": request.POST.get("nombre_inspector") or "",
            "codigo_interno": nueva_inspeccion.codigo_interno,
            "nombre_cliente": request.POST.get("nombre_cliente") or "",
            "rut_cliente": request.POST.get("rut_cliente") or "",
            "email": request.POST.get("email") or "",
            "telefono": request.POST.get("telefono") or "",
            "patente": request.POST.get("patente") or "",
            "anio": request.POST.get("anio") or "",
            "marca": request.POST.get("marca") or "",
            "modelo": request.POST.get("modelo") or "",
            "kilometraje": request.POST.get("kilometraje") or "",
            "color": request.POST.get("color") or "",
            "conclusion": request.POST.get("conclusion") or "",
        }

        # Procesar tabla técnica de inspección
        items_inspeccion = []
        idx_global = 1

        for i, seccion in enumerate(secciones_inspeccion, start=1):
            for j, item in enumerate(seccion["items"], start=1):
                estado = request.POST.get(f"item_estado_{i}_{j}", "Cumple")
                observacion = request.POST.get(f"item_observacion_{i}_{j}", "")
                descripcion = item

                items_inspeccion.append({
                    "numero": f"{i}.{j}",
                    "descripcion": descripcion,
                    "estado": estado,
                    "observacion": observacion
                })

                idx_global += 1

        # Generar el PDF
        pdf_buffer = exportar_informe_inspeccion_pdf(datos_inspeccion, imagenes, items_inspeccion, secciones_inspeccion)

        # Devolver el PDF como respuesta
        response = HttpResponse(pdf_buffer, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="informe_inspeccion_{nueva_inspeccion.codigo_interno}.pdf"'
        return response

    return render(request, "Transaccion/generar_informe_inspeccion_pdf.html", {
        "secciones_inspeccion": secciones_inspeccion
    })


