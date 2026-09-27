import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import PasswordResetCode

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
    PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)
    codigo = generar_codigo()
    vigencia = settings.RECUPERACION_CODIGO_VIGENCIA_SEGUNDOS
    registro = PasswordResetCode.objects.create(
        user=user,
        code_hash=make_password(codigo),
        expires_at=timezone.now() + timedelta(seconds=vigencia),
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
        PasswordResetCode.objects.select_for_update()
        .filter(user=user, is_used=False, expires_at__gt=timezone.now())
        .first()
    )
    if registro is None:
        return CODIGO_INVALIDO, None
    if not check_password(codigo, registro.code_hash):
        registro.attempts += 1
        if registro.attempts >= settings.RECUPERACION_CODIGO_MAX_INTENTOS:
            registro.is_used = True
            registro.save(update_fields=['attempts', 'is_used'])
            return CODIGO_BLOQUEADO, None
        registro.save(update_fields=['attempts'])
        return CODIGO_INVALIDO, None
    # Uso único: desde aquí el código ya no se vuelve a aceptar.
    registro.is_used = True
    registro.save(update_fields=['is_used'])
    return CODIGO_OK, user
