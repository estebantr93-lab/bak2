from django.contrib.auth.models import User
from django.db import models

from core.models import Cargo, Delegacion


class Funcionario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='funcionario')
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name='funcionarios')
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='funcionarios')
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Funcionario'
        verbose_name_plural = 'Funcionarios'

    def __str__(self):
        return self.nombre


class CodigoRecuperacion(models.Model):
    """Código temporal de 6 dígitos para recuperar la contraseña.

    Solo se guarda el hash del código (nunca el texto plano), con su vencimiento,
    los intentos fallidos y si ya fue usado o invalidado.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='codigos_recuperacion')
    codigo_hash = models.CharField(max_length=128)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField()
    intentos = models.PositiveSmallIntegerField(default=0)
    usado = models.BooleanField(default=False)

    class Meta:
        ordering = ['-creado']
        verbose_name = 'Código de recuperación'
        verbose_name_plural = 'Códigos de recuperación'

    def __str__(self):
        return f'{self.user} - {self.creado:%Y-%m-%d %H:%M}'
