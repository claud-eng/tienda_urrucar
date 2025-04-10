import datetime  # Módulo estándar de Python para trabajar con fechas y horas
from django.utils.deprecation import MiddlewareMixin  # Clase base para crear middlewares compatibles con versiones anteriores de Django

class EmpleadoSessionTimeoutMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            return

        try:
            empleado = request.user.empleado
        except:
            return  # No es empleado, se omite

        # Marcar la hora de inicio de sesión si no existe
        if 'session_start_time' not in request.session:
            request.session['session_start_time'] = datetime.datetime.now().isoformat()

        # Comparar si han pasado más de 20 minutos
        session_start = datetime.datetime.fromisoformat(request.session['session_start_time'])
        now = datetime.datetime.now()
        elapsed = (now - session_start).total_seconds()

        if elapsed > 1200:  # 20 minutos
            from django.contrib.auth import logout
            logout(request)
            request.session.flush()
            return
