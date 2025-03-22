import logging # Importa 'logging' para crear registro de logs en un archivo.
from apps.Usuario.models import Cliente, Empleado  # Importa los modelos Cliente y Empleado de la aplicación Usuario
from django.contrib import messages  # Importa la clase para trabajar con mensajes de Django
from django.contrib.auth import logout  # Importa la función logout para cerrar la sesión de un usuario
from django.contrib.auth.decorators import login_required, user_passes_test  # Importa 'login_required' y 'user_passes_test' para proteger vistas que requieren autenticación y permisos.
from django.contrib.auth.hashers import make_password  # Importa la función para crear contraseñas seguras
from django.contrib.auth.models import User  # Importa el modelo User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator  # Importa clases y funciones para paginación
from django.shortcuts import redirect, render  # Importa funciones para redirigir y renderizar plantillas HTML
from .forms import CambiarContraseñaUsuarioForm, ClienteForm, CustomClienteForm, EditarClienteForm, EditarEmpleadoForm, EmpleadoForm  # Importa los formularios definidos en este directorio

# Validación para que solo el administrador tenga acceso a las plantillas
def es_administrador(user):
    return user.is_authenticated and hasattr(user, 'empleado') and user.empleado.rol == 'Administrador'

@user_passes_test(es_administrador, login_url='home')
def listar_clientes(request):
    """
    Lista todos los clientes en la base de datos con opciones de búsqueda
    y paginación. Permite buscar clientes por nombre de usuario.
    """
    clientes = Cliente.objects.all()
    username_query = request.GET.get('username')

    if username_query:
        clientes = clientes.filter(user__username__icontains=username_query)

    paginator = Paginator(clientes, 5)  # Configura paginación para mostrar 5 clientes por página
    page = request.GET.get('page')

    try:
        clientes = paginator.page(page)
    except PageNotAnInteger:
        clientes = paginator.page(1)
    except EmptyPage:
        clientes = paginator.page(paginator.num_pages)

    has_search_query_username = bool(username_query)

    return render(request, 'Usuario/listar_clientes.html', {
        'clientes': clientes,
        'has_search_query_username': has_search_query_username,
    })

def agregar_cliente(request):
    """
    Permite agregar un nuevo cliente mediante un formulario. Si el usuario es un empleado,
    se muestra un mensaje de éxito específico, y si es un cliente, se le indica que puede iniciar sesión.
    """

    # Configuración del logger
    logger = logging.getLogger('usuarios')

    usuario = request.user if request.user.is_authenticated else None

    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            user = User.objects.get(username=form.cleaned_data['username'])
            user.email = form.cleaned_data['username']
            user.save()

            # Determinar si el cliente fue registrado por un administrador/vendedor o por sí mismo
            usuario_registrador = (
                f"{usuario.first_name} {usuario.last_name} ({usuario.email})"
                if usuario else "Autoregistro"
            )

            # **Registrar en el log la acción del usuario**
            logger.info(
                f"Nuevo usuario agregado por {usuario_registrador}:\n"
                f"ID={cliente.id}, Usuario: {user.username}\n"
                f"Nombre: {user.first_name}\n"
                f"Primer Apellido: {user.last_name}\n"
                f"Segundo Apellido: {cliente.second_last_name}\n"
                f"Fecha de Nacimiento: {cliente.fecha_nacimiento.strftime('%d-%m-%Y')}\n"
                f"Número de Teléfono: {cliente.numero_telefono}"
            )

            if usuario and hasattr(usuario, 'empleado') and usuario.empleado.rol in ['Administrador', 'Vendedor']:
                messages.success(request, 'Cliente agregado con éxito.')
                return redirect('listar_clientes')
            else:
                messages.success(request, 'Se ha registrado exitosamente. Puede iniciar sesión ahora.')
                return redirect('login')

    else:
        form = ClienteForm()

    return render(request, "Usuario/agregar_cliente.html", {'form': form})

@user_passes_test(es_administrador, login_url='home')
def editar_cliente(request, cliente_id):
    """
    Permite editar la información de un cliente, incluyendo su nombre de usuario,
    nombre y apellidos.
    """

    # Configuración del logger
    logger = logging.getLogger('usuarios')
    
    usuario = request.user  # Usuario que edita al cliente
    instancia = Cliente.objects.get(id=cliente_id)
    user = instancia.user

    # Guardar valores originales antes de la edición
    valores_anteriores = {
        'Usuario': user.username,
        'Nombre': user.first_name,
        'Primer Apellido': user.last_name,
        'Segundo Apellido': instancia.second_last_name,
        'Fecha de Nacimiento': instancia.fecha_nacimiento.strftime('%d-%m-%Y'),
        'Número de Teléfono': instancia.numero_telefono,
    }

    if request.method == "POST":
        form = EditarClienteForm(request.POST, instance=instancia)
        if form.is_valid():
            # Actualizar los valores del usuario
            user.username = form.cleaned_data['username']
            user.email = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            form.save()

            # Guardar valores nuevos después de la edición
            valores_nuevos = {
                'Usuario': user.username,
                'Nombre': user.first_name,
                'Primer Apellido': user.last_name,
                'Segundo Apellido': instancia.second_last_name,
                'Fecha de Nacimiento': instancia.fecha_nacimiento.strftime('%d-%m-%Y'),
                'Número de Teléfono': instancia.numero_telefono,
            }

            # Detectar cambios
            cambios = []
            for campo, valor_anterior in valores_anteriores.items():
                valor_nuevo = valores_nuevos[campo]
                if valor_anterior != valor_nuevo:
                    cambios.append(f"{campo}: {valor_anterior} -> {valor_nuevo}")

            if cambios:
                logger.info(
                    f"Cliente editado por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
                    f"ID={cliente_id}, Usuario: {user.username}, Nombre: {user.first_name} {user.last_name} {instancia.second_last_name}\n"
                    + "\n".join(cambios)
                )

            messages.success(request, 'Cliente editado con éxito.')
            return redirect('listar_clientes')

    else:
        form = EditarClienteForm(instance=instancia, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    return render(request, "Usuario/editar_cliente.html", {'form': form})

@user_passes_test(es_administrador, login_url='home')
def confirmar_borrar_cliente(request, cliente_id):
    """
    Muestra una página de confirmación antes de eliminar un cliente.
    """
    cliente = Cliente.objects.get(id=cliente_id)
    return render(request, 'Usuario/confirmar_borrar_cliente.html', {'cliente': cliente})

@user_passes_test(es_administrador, login_url='home')
def borrar_cliente(request, cliente_id):
    """
    Elimina un cliente de la base de datos y registra la acción en los logs.
    """

    # Configuración del logger
    logger = logging.getLogger('usuarios')

    usuario = request.user  # Usuario que elimina el cliente

    try:
        cliente = Cliente.objects.get(id=cliente_id)
        cliente_usuario = cliente.user.username  # Guardar nombre de usuario antes de eliminarlo

        cliente.delete()  # Eliminar el cliente

        # **Registrar en el log la acción del usuario**
        logger.info(
            f"Cliente eliminado por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
            f"ID={cliente_id}, Usuario: {cliente_usuario}, Nombre: {cliente.user.first_name} {cliente.user.last_name} {cliente.second_last_name}"
        )

        messages.success(request, "Cliente eliminado con éxito.")

    except Cliente.DoesNotExist:
        messages.error(request, "El cliente no existe.")
        logger.warning(
            f"Intento de eliminación de cliente fallido por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
            f"ID={cliente_id} no existe."
        )

    return redirect("listar_clientes")

@login_required
def actualizar_datos_personales_cliente(request):
    """
    Permite que un cliente actualice su información personal,
    como su nombre de usuario y su fecha de nacimiento.
    """
    user = request.user
    cliente = user.cliente
    
    if request.method == 'POST':
        form = CustomClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            user.username = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            form.save()
            messages.success(request, 'Cambios guardados con éxito.')
    else:
        fecha_nacimiento = cliente.fecha_nacimiento.strftime('%Y-%m-%d') if cliente.fecha_nacimiento else ''
        form = CustomClienteForm(instance=cliente, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'fecha_nacimiento': fecha_nacimiento,
        })
    
    return render(request, 'Usuario/actualizar_datos_personales_cliente.html', {'form': form})

@login_required
def cambiar_contraseña_usuario(request):
    """
    Permite al usuario cambiar su contraseña y cierra su sesión automáticamente
    después de cambiarla.
    """

    # Configuración del logger
    logger = logging.getLogger('usuarios')
    
    usuario = request.user  # Usuario que cambia su contraseña

    # Determinar si es Cliente o Empleado y obtener su ID y segundo apellido
    if hasattr(usuario, 'cliente'):
        tipo_usuario = "Cliente"
        usuario_id = usuario.cliente.id
        segundo_apellido = usuario.cliente.second_last_name
    elif hasattr(usuario, 'empleado'):
        tipo_usuario = "Empleado"
        usuario_id = usuario.empleado.id
        segundo_apellido = usuario.empleado.second_last_name
    else:
        tipo_usuario = "Usuario Desconocido"
        usuario_id = "N/A"
        segundo_apellido = ""

    if request.method == 'POST':
        form = CambiarContraseñaUsuarioForm(request.user, request.POST)
        if form.is_valid():
            form.save()

            # **Registrar en el log la acción del usuario**
            logger.info(
                f"{tipo_usuario} ID={usuario_id}, Usuario: {usuario.email}, Nombre: {usuario.first_name} {usuario.last_name} {segundo_apellido} actualizó su contraseña."
            )

            messages.success(request, 'Contraseña cambiada con éxito.')
            logout(request)  # Cierra la sesión del usuario
            return redirect('login')
    else:
        form = CambiarContraseñaUsuarioForm(request.user)

    return render(request, 'Usuario/cambiar_contraseña_usuario.html', {'form': form})

@user_passes_test(es_administrador, login_url='home')
def listar_empleados(request):
    """
    Lista todos los empleados en la base de datos con opciones de búsqueda y
    paginación. Permite buscar empleados por nombre de usuario y RUT.
    """
    empleados = Empleado.objects.all()
    username_query = request.GET.get('username')
    rut_query = request.GET.get('rut')

    if username_query:
        empleados = empleados.filter(user__username__icontains=username_query)
    if rut_query:
        empleados = empleados.filter(rut__icontains=rut_query)

    paginator = Paginator(empleados, 5)
    page = request.GET.get('page')

    try:
        empleados = paginator.page(page)
    except PageNotAnInteger:
        empleados = paginator.page(1)
    except EmptyPage:
        empleados = paginator.page(paginator.num_pages)

    has_search_query_username = bool(username_query)
    has_search_query_rut = bool(rut_query)

    return render(request, 'Usuario/listar_empleados.html', {
        'empleados': empleados,
        'has_search_query_username': has_search_query_username,
        'has_search_query_rut': has_search_query_rut,
    })

@user_passes_test(es_administrador, login_url='home')
def agregar_empleado(request):
    """
    Permite agregar un nuevo empleado mediante un formulario y configura su correo electrónico
    basado en el nombre de usuario ingresado.
    """

    # Configuración del logger
    logger = logging.getLogger('usuarios')

    usuario = request.user  # El usuario que agrega el empleado (siempre será un administrador)

    if request.method == "POST":
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            empleado = form.save()
            user = User.objects.get(username=form.cleaned_data['username'])
            user.email = form.cleaned_data['username']
            user.save()

            # **Registrar en el log la acción del administrador**
            logger.info(
                f"Nuevo empleado agregado por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
                f"ID={empleado.id}, Usuario: {user.username}\n"
                f"RUT: {empleado.rut}\n"
                f"Nombre: {user.first_name}\n"
                f"Primer Apellido: {user.last_name}\n"
                f"Segundo Apellido: {empleado.second_last_name}\n"
                f"Fecha de Nacimiento: {empleado.fecha_nacimiento.strftime('%d-%m-%Y')}\n"
                f"Número de Teléfono: {empleado.numero_telefono}\n"
                f"Rol: {empleado.rol}"
            )

            messages.success(request, 'Empleado agregado con éxito.')
            return redirect('listar_empleados')

    else:
        form = EmpleadoForm()

    return render(request, "Usuario/agregar_empleado.html", {'form': form})

@user_passes_test(es_administrador, login_url='home')
def editar_empleado(request, empleado_id):
    """
    Permite editar la información de un empleado, incluyendo su nombre de usuario,
    nombre y apellidos.
    """

    # Configuración del logger
    logger = logging.getLogger('usuarios')

    usuario = request.user  # Usuario que edita el empleado
    instancia = Empleado.objects.get(id=empleado_id)
    user = instancia.user

    # Restricción: Un Administrador NO puede editar a otro Administrador, pero sí puede editarse a sí mismo
    if request.user.empleado.rol == "Administrador" and instancia.rol == "Administrador" and request.user != user:
        messages.error(request, "No tienes permiso para editar a otro administrador.")
        return redirect("listar_empleados")  # Redirigir al listado de empleados

    # Guardar valores originales antes de la edición
    valores_anteriores = {
        'Usuario': user.username,
        'RUT': instancia.rut,
        'Nombre': user.first_name,
        'Primer Apellido': user.last_name,
        'Segundo Apellido': instancia.second_last_name,
        'Fecha de Nacimiento': instancia.fecha_nacimiento.strftime('%d-%m-%Y'),
        'Número de Teléfono': instancia.numero_telefono,
        'Rol': instancia.rol,
    }

    if request.method == "POST":
        form = EditarEmpleadoForm(request.POST, instance=instancia)
        if form.is_valid():
            # Actualizar los valores del usuario
            user.username = form.cleaned_data['username']
            user.email = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            form.save()

            # Guardar valores nuevos después de la edición
            valores_nuevos = {
                'Usuario': user.username,
                'RUT': instancia.rut,
                'Nombre': user.first_name,
                'Primer Apellido': user.last_name,
                'Segundo Apellido': instancia.second_last_name,
                'Fecha de Nacimiento': instancia.fecha_nacimiento.strftime('%d-%m-%Y'),
                'Número de Teléfono': instancia.numero_telefono,
                'Rol': instancia.rol,
            }

            # Detectar cambios
            cambios = []
            for campo, valor_anterior in valores_anteriores.items():
                valor_nuevo = valores_nuevos[campo]
                if valor_anterior != valor_nuevo:
                    cambios.append(f"{campo}: {valor_anterior} -> {valor_nuevo}")

            if cambios:
                logger.info(
                    f"Empleado editado por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
                    f"ID={empleado_id}, Usuario: {user.username}, Nombre: {user.first_name} {user.last_name} {instancia.second_last_name}\n"
                    + "\n".join(cambios)
                )

            messages.success(request, "Empleado editado con éxito.")
            return redirect("listar_empleados")

    else:
        form = EditarEmpleadoForm(instance=instancia, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    return render(request, "Usuario/editar_empleado.html", {'form': form})

@user_passes_test(es_administrador, login_url='home')
def confirmar_borrar_empleado(request, empleado_id):
    """
    Muestra una página de confirmación antes de eliminar un empleado,
    pero impide que un Administrador intente eliminar a otro Administrador.
    """

    empleado = Empleado.objects.get(id=empleado_id)

    # Restricción: Un Administrador NO puede eliminar a otro Administrador
    if request.user.empleado.rol == "Administrador" and empleado.rol == "Administrador":
        messages.error(request, "No tienes permiso para eliminar a otro administrador o a ti mismo.")
        return redirect("listar_empleados")  # Redirigir al listado de empleados

    return render(request, 'Usuario/confirmar_borrar_empleado.html', {'empleado': empleado})

@user_passes_test(es_administrador, login_url='home')
def borrar_empleado(request, empleado_id):
    """
    Elimina un empleado de la base de datos y registra la acción en los logs.
    """

    # Configuración del logger
    logger = logging.getLogger('usuarios')

    usuario = request.user  # Usuario que elimina el empleado

    try:
        empleado = Empleado.objects.get(id=empleado_id)

        # Restricción: Un Administrador NO puede eliminar a otro Administrador
        if usuario.empleado.rol == "Administrador" and empleado.rol == "Administrador":
            messages.error(request, "No tienes permiso para eliminar a otro administrador o a ti mismo.")
            logger.warning(
                f"Intento de eliminación bloqueado: {usuario.first_name} {usuario.last_name} ({usuario.email}) "
                f"intentó eliminar a otro Administrador (ID={empleado_id}, Usuario: {empleado.user.username})."
            )
            return redirect("listar_empleados")
        
        empleado_usuario = empleado.user.username  # Guardar nombre de usuario antes de eliminarlo

        empleado.delete()  # Eliminar el empleado

        # **Registrar en el log la acción del usuario**
        logger.info(
            f"Empleado eliminado por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
            f"ID={empleado_id}, Usuario: {empleado_usuario}, Nombre: {empleado.user.first_name} {empleado.user.last_name} {empleado.second_last_name}"
        )

        messages.success(request, "Empleado eliminado con éxito.")

    except Empleado.DoesNotExist:
        messages.error(request, "El empleado no existe.")
        logger.warning(
            f"Intento de eliminación de empleado fallido por {usuario.first_name} {usuario.last_name} ({usuario.email}):\n"
            f"ID={empleado_id} no existe."
        )

    return redirect("listar_empleados")

@user_passes_test(es_administrador, login_url='home')
def gestionar_cuentas(request):
    """
    Muestra la página de gestión de cuentas para administradores o usuarios
    autorizados.
    """
    return render(request, 'Usuario/gestionar_cuentas.html')
