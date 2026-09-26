from django.db import models

from core.models import Delegacion
from funcionarios.models import Funcionario


class Compromiso(models.Model):
    ESTADO_CHOICES = [
        ('ingresado', 'Ingresado'),
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('realizado', 'Realizado'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name='compromisos')
    responsable = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='compromisos'
    )
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ingresado')
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_vencimiento']
        verbose_name = 'Compromiso'
        verbose_name_plural = 'Compromisos'

    def __str__(self):
        return self.titulo


class SeguimientoCompromiso(models.Model):
    compromiso = models.ForeignKey(Compromiso, on_delete=models.CASCADE, related_name='seguimientos')
    fecha = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(
        Funcionario, on_delete=models.SET_NULL, null=True, blank=True, related_name='seguimientos'
    )
    descripcion = models.TextField()
    estado_nuevo = models.CharField(max_length=20, choices=Compromiso.ESTADO_CHOICES)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Seguimiento de compromiso'
        verbose_name_plural = 'Seguimientos de compromiso'

    def __str__(self):
        return f'{self.compromiso.titulo} - {self.estado_nuevo}'
