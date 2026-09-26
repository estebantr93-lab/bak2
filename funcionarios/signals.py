from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver


@receiver(user_logged_in)
def mensaje_ingreso(sender, request, user, **kwargs):
    if request is not None and hasattr(request, '_messages'):
        messages.success(request, f'Bienvenido/a, {user.get_full_name() or user.get_username()}.')


@receiver(user_logged_out)
def mensaje_salida(sender, request, user, **kwargs):
    # logout() limpia la sesión después de esta señal; el mensaje viaja en su propia cookie.
    if request is not None and hasattr(request, '_messages'):
        messages.info(request, 'Sesión cerrada correctamente.')
