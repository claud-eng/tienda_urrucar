from apps.Usuario.models import Cliente, Empleado  # Importa los modelos Cliente y Empleado de la aplicación Usuario
from django.contrib import messages  # Importa la clase para trabajar con mensajes de Django
from django.contrib.auth import logout  # Importa la función logout para cerrar la sesión de un usuario
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password  # Importa la función para crear contraseñas seguras
from django.contrib.auth.models import User  # Importa el modelo User
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator  # Importa clases y funciones para paginación
from django.shortcuts import redirect, render  # Importa funciones para redirigir y renderizar plantillas HTML
from .forms import CambiarContraseñaClienteForm, ClienteForm, CustomClienteForm, EditarClienteForm, EditarEmpleadoForm, EmpleadoForm  # Importa los formularios definidos en este directorio

@login_required
def listar_clientes(request):
    """
    Lista todos los clientes en la base de datos con opciones de búsqueda
    y paginación. Permite buscar clientes por nombre de usuario y RUT.
    """
    clientes = Cliente.objects.all()
    username_query = request.GET.get('username')
    rut_query = request.GET.get('rut')

    if username_query:
        clientes = clientes.filter(user__username__icontains=username_query)
    if rut_query:
        clientes = clientes.filter(rut__icontains=rut_query)

    paginator = Paginator(clientes, 5)  # Configura paginación para mostrar 5 clientes por página
    page = request.GET.get('page')

    try:
        clientes = paginator.page(page)
    except PageNotAnInteger:
        clientes = paginator.page(1)
    except EmptyPage:
        clientes = paginator.page(paginator.num_pages)

    has_search_query_username = bool(username_query)
    has_search_query_rut = bool(rut_query)

    return render(request, 'Usuario/listar_clientes.html', {
        'clientes': clientes,
        'has_search_query_username': has_search_query_username,
        'has_search_query_rut': has_search_query_rut,
    })

def agregar_cliente(request):
    """
    Permite agregar un nuevo cliente mediante un formulario. Si el usuario es un empleado,
    se muestra un mensaje de éxito específico, y si es un cliente, se le indica que puede iniciar sesión.
    """
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            user = User.objects.get(username=form.cleaned_data['username'])
            user.email = form.cleaned_data['username']
            user.save()

            if request.user.is_authenticated and request.user.empleado and (request.user.empleado.rol == 'Administrador' or request.user.empleado.rol == 'Vendedor'):
                messages.success(request, 'Cliente agregado con éxito.')
                return redirect('listar_clientes')
            else:
                messages.success(request, 'Se ha registrado exitosamente. Puede iniciar sesión ahora.')
                return redirect('login')
    else:
        form = ClienteForm()
    return render(request, "Usuario/agregar_cliente.html", {'form': form})

@login_required
def confirmar_borrar_cliente(request, cliente_id):
    """
    Muestra una página de confirmación antes de eliminar un cliente.
    """
    cliente = Cliente.objects.get(id=cliente_id)
    return render(request, 'Usuario/confirmar_borrar_cliente.html', {'cliente': cliente})

@login_required
def borrar_cliente(request, cliente_id):
    """
    Elimina un cliente de la base de datos y redirige a la lista de clientes.
    """
    try:
        instancia = Cliente.objects.get(id=cliente_id)
        instancia.delete()
        messages.success(request, 'Cliente eliminado con éxito.')
    except Cliente.DoesNotExist:
        pass  # Si el cliente no existe, no se hace nada
    return redirect('listar_clientes')

@login_required
def editar_cliente(request, cliente_id):
    """
    Permite editar la información de un cliente, incluyendo su nombre de usuario,
    nombre y apellidos.
    """
    instancia = Cliente.objects.get(id=cliente_id)
    user = instancia.user

    if request.method == "POST":
        form = EditarClienteForm(request.POST, instance=instancia)
        if form.is_valid():
            user.username = form.cleaned_data['username']
            user.email = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            form.save()

            messages.success(request, 'Cliente editado con éxito.')
            return redirect('listar_clientes')
    else:
        form = EditarClienteForm(instance=instancia, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    return render(request, "Usuario/editar_cliente.html", {'form': form})

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
def cambiar_contraseña_cliente(request):
    """
    Permite al cliente cambiar su contraseña y cierra su sesión automáticamente
    después de cambiarla.
    """
    if request.method == 'POST':
        form = CambiarContraseñaClienteForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contraseña cambiada con éxito.')
            logout(request)  # Cierra la sesión del usuario
            return redirect('login')
    else:
        form = CambiarContraseñaClienteForm(request.user)

    return render(request, 'Usuario/cambiar_contraseña_cliente.html', {'form': form})

@login_required
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

@login_required
def agregar_empleado(request):
    """
    Permite agregar un nuevo empleado mediante un formulario y configura su correo electrónico
    basado en el nombre de usuario ingresado.
    """
    if request.method == "POST":
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            empleado = form.save()
            user = User.objects.get(username=form.cleaned_data['username'])
            user.email = form.cleaned_data['username']
            user.save()
            messages.success(request, 'Empleado agregado con éxito.')
            return redirect('listar_empleados')
    else:
        form = EmpleadoForm()
    return render(request, "Usuario/agregar_empleado.html", {'form': form})

@login_required
def confirmar_borrar_empleado(request, empleado_id):
    """
    Muestra una página de confirmación antes de eliminar un empleado.
    """
    empleado = Empleado.objects.get(id=empleado_id)
    return render(request, 'Usuario/confirmar_borrar_empleado.html', {'empleado': empleado})

@login_required
def borrar_empleado(request, empleado_id):
    """
    Elimina un empleado de la base de datos y redirige a la lista de empleados.
    """
    try:
        instancia = Empleado.objects.get(id=empleado_id)
        instancia.delete()
        messages.success(request, 'Empleado eliminado con éxito.')
    except Empleado.DoesNotExist:
        pass
    return redirect('listar_empleados')

@login_required
def editar_empleado(request, empleado_id):
    """
    Permite editar la información de un empleado, incluyendo su nombre de usuario,
    nombre y apellidos.
    """
    instancia = Empleado.objects.get(id=empleado_id)
    user = instancia.user

    if request.method == "POST":
        form = EditarEmpleadoForm(request.POST, instance=instancia)
        if form.is_valid():
            user.username = form.cleaned_data['username']
            user.email = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            form.save()
            messages.success(request, 'Empleado editado con éxito.')
            return redirect('listar_empleados')
    else:
        form = EditarEmpleadoForm(instance=instancia, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    return render(request, "Usuario/editar_empleado.html", {'form': form})

@login_required
def gestionar_cuentas(request):
    """
    Muestra la página de gestión de cuentas para administradores o usuarios
    autorizados.
    """
    return render(request, 'Usuario/gestionar_cuentas.html')
