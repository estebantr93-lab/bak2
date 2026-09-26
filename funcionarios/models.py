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
