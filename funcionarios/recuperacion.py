import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import CodigoRecuperacion

CODIGO_OK = 'ok'
CODIGO_INVALIDO = 'invalido'
CODIGO_BLOQUEADO = 'bloqueado'


def generar_codigo():
    """6 dígitos con el generador criptográfico (no predecible)."""
    return f'{secrets.randbelow(10**6):06d}'


def usuario_por_correo(email):
    return User.objects.filter(email__iexact=email.strip(), is_active=True).order_by('pk').first()


@transaction.atomic
def solicitar_codigo(email):
    """Genera y envía un código si el correo existe. No informa si existe o no."""
    user = usuario_por_correo(email)
    if user is None:
        return None
    # Pedir un código nuevo invalida los anteriores.
    CodigoRecuperacion.objects.filter(user=user, usado=False).update(usado=True)
    codigo = generar_codigo()
    vigencia = settings.RECUPERACION_CODIGO_VIGENCIA_SEGUNDOS
    registro = CodigoRecuperacion.objects.create(
        user=user,
        codigo_hash=make_password(codigo),
        expira=timezone.now() + timedelta(seconds=vigencia),
    )
    send_mail(
        'SGR · Código de recuperación de contraseña',
        f'Su código de recuperación es: {codigo}\n\n'
        f'Vence en {vigencia} segundos y sirve una sola vez. '
        'Si usted no lo solicitó, ignore este mensaje.',
        None,
        [user.email],
    )
    return registro


@transaction.atomic
def validar_codigo(email, codigo):
    """Devuelve (estado, user). Cuenta intentos y marca el código como usado si es correcto."""
    user = usuario_por_correo(email or '')
    if user is None:
        return CODIGO_INVALIDO, None
    registro = (
        CodigoRecuperacion.objects.select_for_update()
        .filter(user=user, usado=False, expira__gt=timezone.now())
        .first()
    )
    if registro is None:
        return CODIGO_INVALIDO, None
    if not check_password(codigo, registro.codigo_hash):
        registro.intentos += 1
        if registro.intentos >= settings.RECUPERACION_CODIGO_MAX_INTENTOS:
            registro.usado = True
            registro.save(update_fields=['intentos', 'usado'])
            return CODIGO_BLOQUEADO, None
        registro.save(update_fields=['intentos'])
        return CODIGO_INVALIDO, None
    # Uso único: desde aquí el código ya no se vuelve a aceptar.
    registro.usado = True
    registro.save(update_fields=['usado'])
    return CODIGO_OK, user
