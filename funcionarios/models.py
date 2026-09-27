from django.contrib.auth.models import User
from django.db import models

from core.models import Position, Delegation


class Employee(models.Model):
    user = models.OneToOneField(User, verbose_name='usuario', on_delete=models.CASCADE, related_name='employee')
    delegation = models.ForeignKey(Delegation, verbose_name='delegación', on_delete=models.PROTECT, related_name='employees')
    position = models.ForeignKey(Position, verbose_name='cargo', on_delete=models.PROTECT, related_name='employees')
    name = models.CharField('nombre', max_length=150)
    is_active = models.BooleanField('activo', default=True)


    owner_field = ''  # el propio registro: un funcionario solo puede elegirse a sí mismo
    class Meta:
        db_table = 'employee'
        ordering = ['name']
        verbose_name = 'Funcionario'
        verbose_name_plural = 'Funcionarios'

    def __str__(self):
        return self.name


class PasswordResetCode(models.Model):
    """Código temporal de 6 dígitos para recuperar la contraseña.

    Solo se guarda el hash del código (nunca el texto plano), con su vencimiento,
    los intentos fallidos y si ya fue usado o invalidado.
    """

    user = models.ForeignKey(User, verbose_name='usuario', on_delete=models.CASCADE, related_name='password_reset_codes')
    code_hash = models.CharField('hash del código', max_length=128)
    created_at = models.DateTimeField('creado', auto_now_add=True)
    expires_at = models.DateTimeField('expira')
    attempts = models.PositiveSmallIntegerField('intentos', default=0)
    is_used = models.BooleanField('usado', default=False)

    class Meta:
        db_table = 'password_reset_code'
        ordering = ['-created_at']
        verbose_name = 'Código de recuperación'
        verbose_name_plural = 'Códigos de recuperación'

    def __str__(self):
        return f'{self.user} - {self.created_at:%Y-%m-%d %H:%M}'
