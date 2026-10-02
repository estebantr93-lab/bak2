"""Registro de accesos y límite de intentos de ingreso.

- OWASP A09 (registro y monitoreo): cada ingreso correcto o fallido, cada bloqueo, cada cierre de
  sesión y cada acceso denegado (403) queda en la traza de auditoría con usuario, IP y fecha. Nunca
  se guarda la contraseña.
- OWASP A07 (identificación y autenticación): el conteo de esos ingresos fallidos bloquea por un
  tiempo un nombre de usuario (fuerza bruta) y una IP (una clave probada contra muchas cuentas).

El conteo se hace sobre la base de datos y no en memoria, así vale igual con varios procesos de
gunicorn.
"""
import ipaddress
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.shortcuts import render
from django.utils import timezone

from colaboracion.models import AuditLog

ENTIDAD = 'Acceso'
LOGIN_EXITOSO = 'login_exitoso'
LOGIN_FALLIDO = 'login_fallido'
LOGIN_BLOQUEADO = 'login_bloqueado'
# Clave correcta, pero la cuenta no puede entrar (sin rol, sin perfil, desactivada). El usuario ve el
# mismo mensaje que con una clave incorrecta; el motivo queda aquí para el administrador.
LOGIN_RECHAZADO = 'login_rechazado'
LOGOUT = 'logout'
ACCESO_DENEGADO = 'acceso_denegado'


def ip_cliente(request):
    """IP de quien hace la petición. Detrás de nginx, la última de X-Forwarded-For (la agrega nginx)."""
    if request is None:
        return None
    ip = request.META.get('REMOTE_ADDR', '')
    if settings.CONFIAR_X_FORWARDED_FOR:
        reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if reenviada:
            ip = reenviada.split(',')[-1].strip()
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        return None


def normalizar(username):
    return (username or '').strip().lower()[:150]


def registrar_acceso(request, accion, detalle='', user=None, motivo=''):
    if user is None and request is not None and getattr(request, 'user', None) and request.user.is_authenticated:
        user = request.user
    AuditLog.objects.create(user=user, action=accion, entity_type=ENTIDAD, detail=detalle, ip=ip_cliente(request),
                            changes={'motivo': ['', motivo]} if motivo else {})


def _fallidos(desde, **filtro):
    # Los rechazos con la clave correcta también cuentan: si no, el bloqueo dejaría ver cuándo se acertó.
    return AuditLog.objects.filter(action__in=(LOGIN_FALLIDO, LOGIN_RECHAZADO), entity_type=ENTIDAD,
                                   date__gte=desde, **filtro).count()


def esta_bloqueado(request, username):
    """True si el usuario o la IP superaron los intentos fallidos permitidos en la ventana de tiempo."""
    inicio = timezone.now() - timedelta(minutes=settings.LOGIN_VENTANA_MINUTOS)
    nombre = normalizar(username)
    # Para el usuario solo cuentan los fallos posteriores a su último ingreso correcto.
    ultimo_ingreso = (
        AuditLog.objects.filter(action=LOGIN_EXITOSO, entity_type=ENTIDAD, detail=nombre, date__gte=inicio)
        .order_by('-date').values_list('date', flat=True).first()
    )
    if _fallidos(ultimo_ingreso or inicio, detail=nombre) >= settings.LOGIN_MAX_INTENTOS:
        return True
    ip = ip_cliente(request)
    return bool(ip) and _fallidos(inicio, ip=ip) >= settings.LOGIN_MAX_INTENTOS_IP


@receiver(user_login_failed)
def _ingreso_fallido(sender, credentials, request=None, **kwargs):
    # credentials trae la contraseña enmascarada por Django; solo se guarda el nombre de usuario.
    registrar_acceso(request, LOGIN_FALLIDO, normalizar(credentials.get('username')))


@receiver(user_logged_in)
def _ingreso_correcto(sender, request, user, **kwargs):
    registrar_acceso(request, LOGIN_EXITOSO, normalizar(user.get_username()), user=user)


@receiver(user_logged_out)
def _cierre_de_sesion(sender, request, user, **kwargs):
    if user is not None:
        registrar_acceso(request, LOGOUT, normalizar(user.get_username()), user=user)


def acceso_denegado(request, exception=None):
    """handler403: registra el intento (usuario, ruta e IP) y muestra la página de acceso denegado."""
    registrar_acceso(request, ACCESO_DENEGADO, request.path[:500])
    mensaje = str(exception) if exception and str(exception) else ''
    return render(request, '403.html', {'exception': mensaje}, status=403)
