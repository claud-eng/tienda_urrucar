from django.shortcuts import redirect, render  # Importa funciones para redirigir y renderizar plantillas HTML
from apps.Usuario.models import Cliente, Empleado  # Importa los modelos Cliente y Empleado de la aplicación Usuario
from .forms import ClienteForm, EmpleadoForm, EditarClienteForm, EditarEmpleadoForm  # Importa los formularios definidos en este directorio
from django.contrib import messages  # Importa la clase para trabajar con mensajes de Django
from django.contrib.auth.hashers import make_password  # Importa la función para crear contraseñas seguras
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage  # Importa clases y funciones para paginación
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomClienteForm
from .forms import CambiarContraseñaClienteForm
from django.contrib.auth.models import User  # Importa el modelo User
from django.contrib.auth import logout

@login_required
def listar_clientes(request):
    # Vista para listar clientes con opciones de búsqueda y paginación

    # Obtener todos los clientes
    clientes = Cliente.objects.all()

    # Obtener los valores de búsqueda de los parámetros 'username' y 'rut' en la URL
    username_query = request.GET.get('username')
    rut_query = request.GET.get('rut')

    # Si se proporcionó un valor de búsqueda de nombre de usuario, filtrar clientes por nombre de usuario
    if username_query:
        clientes = clientes.filter(user__username__icontains=username_query)

    # Si se proporcionó un valor de búsqueda de RUT, filtrar clientes por RUT
    if rut_query:
        clientes = clientes.filter(rut__icontains=rut_query)

    # Configurar la paginación
    paginator = Paginator(clientes, 5)  # Mostrar 5 clientes por página
    page = request.GET.get('page')  # Obtener el número de página de la solicitud GET

    try:
        clientes = paginator.page(page)
    except PageNotAnInteger:
        clientes = paginator.page(1)  # Si la página no es un número entero, mostrar la primera página
    except EmptyPage:
        clientes = paginator.page(paginator.num_pages)  # Si la página está fuera de rango, mostrar la última página

    # Agregar variables de contexto para indicar si se ha realizado una búsqueda
    has_search_query_username = bool(username_query)
    has_search_query_rut = bool(rut_query)

    return render(request, 'Usuario/listar_clientes.html', {
        'clientes': clientes,
        'has_search_query_username': has_search_query_username,
        'has_search_query_rut': has_search_query_rut,
    })

def agregar_cliente(request):
    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            # Guarda el formulario y obtiene el cliente
            cliente = form.save()

            # Actualiza el campo 'email' en el modelo User
            user = User.objects.get(username=form.cleaned_data['username'])
            user.email = form.cleaned_data['username']
            user.save()

            if request.user.is_authenticated and request.user.empleado and (request.user.empleado.rol == 'Administrador' or request.user.empleado.rol == 'Vendedor'):
                # Si el usuario es un empleado, muestra el mensaje de éxito para el cliente agregado
                messages.success(request, 'Cliente agregado con éxito.')
                return redirect('listar_clientes')
            else:
                # Si el usuario no está autenticado, muestra el mensaje de éxito para el registro
                messages.success(request, 'Se ha registrado exitosamente. Puede iniciar sesión ahora.')
                return redirect('login')
    else:
        form = ClienteForm()
    return render(request, "Usuario/agregar_cliente.html", {'form': form})

@login_required
def confirmar_borrar_cliente(request, cliente_id):
    # Vista para confirmar la eliminación de un cliente

    cliente = Cliente.objects.get(id=cliente_id)
    return render(request, 'Usuario/confirmar_borrar_cliente.html', {'cliente': cliente})

@login_required
def borrar_cliente(request, cliente_id):
    # Vista para borrar un cliente existente

    try:
        instancia = Cliente.objects.get(id=cliente_id)
        instancia.delete()
        messages.success(request, 'Cliente eliminado con éxito.')  # Agrega mensaje de éxito
    except Cliente.DoesNotExist:
        pass  # Manejar la situación en la que el cliente no existe

    return redirect('listar_clientes')  # Redirige a la lista de clientes después de borrar

@login_required
def editar_cliente(request, cliente_id):
    instancia = Cliente.objects.get(id=cliente_id)
    user = instancia.user  # Obtener el usuario existente

    if request.method == "POST":
        form = EditarClienteForm(request.POST, instance=instancia)
        if form.is_valid():
            # Actualizar el usuario existente con el nuevo username
            user.username = form.cleaned_data['username']
            # Aquí se actualiza el email con el nuevo valor del username
            user.email = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()  # Guardar el usuario actualizado

            # Continuar con la actualización del cliente
            cliente = form.save()

            messages.success(request, 'Cliente editado con éxito.')
            return redirect('listar_clientes')
    else:
        # Pasar los valores actuales como valores iniciales al formulario
        form = EditarClienteForm(instance=instancia, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    return render(request, "Usuario/editar_cliente.html", {'form': form})

@login_required
def actualizar_datos_personales_cliente(request):
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
        # En el bloque "else", crea el formulario con datos iniciales adecuados
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
    if request.method == 'POST':
        form = CambiarContraseñaClienteForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Contraseña cambiada con éxito.')
            
            # Cerrar la sesión del usuario
            logout(request)
            
            # Redirigir al usuario a la página de inicio de sesión
            return redirect('login')

    else:
        form = CambiarContraseñaClienteForm(request.user)

    return render(request, 'Usuario/cambiar_contraseña_cliente.html', {'form': form})

@login_required
def listar_empleados(request):
    # Vista para listar empleados con opciones de búsqueda y paginación

    # Obtener todos los empleados
    empleados = Empleado.objects.all()

    # Obtener los valores de búsqueda de los parámetros 'username' y 'rut' en la URL
    username_query = request.GET.get('username')
    rut_query = request.GET.get('rut')

    # Si se proporcionó un valor de búsqueda de nombre de usuario, filtrar empleados por nombre de usuario
    if username_query:
        empleados = empleados.filter(user__username__icontains=username_query)

    # Si se proporcionó un valor de búsqueda de RUT, filtrar empleados por RUT
    if rut_query:
        empleados = empleados.filter(rut__icontains=rut_query)

    # Configurar la paginación
    paginator = Paginator(empleados, 5)  # Mostrar 5 empleados por página
    page = request.GET.get('page')  # Obtener el número de página de la solicitud GET

    try:
        empleados = paginator.page(page)
    except PageNotAnInteger:
        empleados = paginator.page(1)  # Si la página no es un número entero, mostrar la primera página
    except EmptyPage:
        empleados = paginator.page(paginator.num_pages)  # Si la página está fuera de rango, mostrar la última página

    # Agregar variables de contexto para indicar si se ha realizado una búsqueda
    has_search_query_username = bool(username_query)
    has_search_query_rut = bool(rut_query)

    return render(request, 'Usuario/listar_empleados.html', {
        'empleados': empleados,
        'has_search_query_username': has_search_query_username,
        'has_search_query_rut': has_search_query_rut,
    })

@login_required
def agregar_empleado(request):
    if request.method == "POST":
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            # Guarda el formulario y obtiene el empleado
            empleado = form.save()

            # Actualiza el campo 'email' en el modelo User
            user = User.objects.get(username=form.cleaned_data['username'])
            user.email = form.cleaned_data['username']
            user.save()
            messages.success(request, 'Empleado agregado con éxito.')  # Agrega mensaje de éxito
            return redirect('listar_empleados')  # Redirige a la lista de empleados después de agregar uno nuevo
    else:
        form = EmpleadoForm()
    return render(request, "Usuario/agregar_empleado.html", {'form': form})

@login_required
def confirmar_borrar_empleado(request, empleado_id):
    # Vista para confirmar la eliminación de un empleado

    empleado = Empleado.objects.get(id=empleado_id)
    return render(request, 'Usuario/confirmar_borrar_empleado.html', {'empleado': empleado})

@login_required
def borrar_empleado(request, empleado_id):
    # Vista para borrar un empleado existente

    try:
        instancia = Empleado.objects.get(id=empleado_id)
        instancia.delete()
        messages.success(request, 'Empleado eliminado con éxito.')  # Agrega mensaje de éxito
    except Empleado.DoesNotExist:
        pass  # Manejar la situación en la que el empleado no existe

    return redirect('listar_empleados')  # Redirige a la lista de empleados después de borrar

@login_required
def editar_empleado(request, empleado_id):
    instancia = Empleado.objects.get(id=empleado_id)
    user = instancia.user  # Obtener el usuario existente

    if request.method == "POST":
        form = EditarEmpleadoForm(request.POST, instance=instancia)
        if form.is_valid():
            # Actualizar el usuario existente con el nuevo username
            user.username = form.cleaned_data['username']
            # Aquí se actualiza el email con el nuevo valor del username
            user.email = form.cleaned_data['username']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()  # Guardar el usuario actualizado

            # Continuar con la actualización del empleado
            empleado = form.save()

            messages.success(request, 'Empleado editado con éxito.')
            return redirect('listar_empleados')
    else:
        # Pasar los valores actuales como valores iniciales al formulario
        form = EditarEmpleadoForm(instance=instancia, initial={
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })

    return render(request, "Usuario/editar_empleado.html", {'form': form})

@login_required
def gestionar_cuentas(request):
    # Aquí puedes agregar la lógica para gestionar cuentas de usuarios
    return render(request, 'Usuario/gestionar_cuentas.html')
