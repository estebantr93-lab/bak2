import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .forms import LoginForm, SolicitarCodigoForm, ValidarCodigoForm
from .recuperacion import CODIGO_BLOQUEADO, CODIGO_OK, solicitar_codigo, validar_codigo

# Estado temporal del flujo en la sesión (no se guarda el código, solo el correo y el paso validado).
SESION_EMAIL = 'recuperacion_email'
SESION_VALIDADO = 'recuperacion_validado'
# Ventana para definir la nueva contraseña una vez validado el código.
VENTANA_NUEVA_CLAVE_SEGUNDOS = 300

MENSAJE_GENERICO = (
    'Si el correo corresponde a una cuenta registrada, recibirá un código de 6 dígitos. '
    'Revise su bandeja de entrada.'
)


class IngresoView(LoginView):
    """Login de Django que, si se abre con una sesión activa, la cierra.

    Pasa, por ejemplo, al usar «atrás» después de ingresar: la página de ingreso ya no muestra un
    formulario con la sesión todavía abierta, y «adelante» no vuelve a entrar sin la clave. (Django
    marca esta página como no almacenable, así que el navegador siempre la vuelve a pedir.)"""

    authentication_form = LoginForm

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            request.cierre_por_seguridad = True  # el aviso lo da funcionarios/signals.py
            logout(request)  # también registra el cierre en la traza (user_logged_out)
        return super().get(request, *args, **kwargs)


def _limpiar_sesion(request):
    request.session.pop(SESION_EMAIL, None)
    request.session.pop(SESION_VALIDADO, None)


def solicitar(request):
    form = SolicitarCodigoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email']
        solicitar_codigo(email)
        _limpiar_sesion(request)
        request.session[SESION_EMAIL] = email
        # Respuesta idéntica exista o no el correo.
        messages.info(request, MENSAJE_GENERICO)
        return redirect('recuperar_codigo')
    return render(request, 'registration/recuperar_solicitar.html', {'form': form})


def ingresar_codigo(request):
    email = request.session.get(SESION_EMAIL)
    if not email:
        return redirect('recuperar_solicitar')
    form = ValidarCodigoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        estado, user = validar_codigo(email, form.cleaned_data['code'])
        if estado == CODIGO_OK:
            request.session.pop(SESION_EMAIL, None)
            request.session[SESION_VALIDADO] = {'user_id': user.pk, 'hasta': time.time() + VENTANA_NUEVA_CLAVE_SEGUNDOS}
            return redirect('recuperar_nueva')
        if estado == CODIGO_BLOQUEADO:
            _limpiar_sesion(request)
            messages.error(request, 'Superó el máximo de intentos. Solicite un nuevo código.')
            return redirect('recuperar_solicitar')
        form.add_error('code', 'Código incorrecto o vencido.')
    return render(request, 'registration/recuperar_codigo.html', {
        'form': form,
        'vigencia': settings.RECUPERACION_CODIGO_VIGENCIA_SEGUNDOS,
        'max_intentos': settings.RECUPERACION_CODIGO_MAX_INTENTOS,
    })


def nueva_contrasena(request):
    validado = request.session.get(SESION_VALIDADO)
    if not validado or validado.get('hasta', 0) < time.time():
        _limpiar_sesion(request)
        messages.error(request, 'La validación expiró. Solicite un nuevo código.')
        return redirect('recuperar_solicitar')
    user = User.objects.filter(pk=validado['user_id'], is_active=True).first()
    if user is None:
        _limpiar_sesion(request)
        return redirect('recuperar_solicitar')
    form = SetPasswordForm(user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()  # usa set_password() y aplica los validadores de contraseña
        _limpiar_sesion(request)
        messages.success(request, 'Contraseña actualizada. Ya puede ingresar con su nueva contraseña.')
        return redirect('login')
    return render(request, 'registration/recuperar_nueva.html', {'form': form})
