import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from actividades.models import Actividad


class Evidencia(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    codigo_unico = models.CharField(max_length=40, unique=True, blank=True)
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='evidencias')
    descripcion = models.TextField(blank=True)
    archivo = models.FileField(upload_to='evidencias/%Y/%m/', blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    resultado = models.CharField(max_length=200, blank=True)
    revisada_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='revisiones'
    )

    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Evidencia'
        verbose_name_plural = 'Evidencias'
        permissions = [
            ('can_approve_evidencia', 'Puede aprobar evidencias'),
        ]

    def __str__(self):
        return self.codigo_unico

    @staticmethod
    def generar_codigo_unico():
        return f'EVI-{timezone.now():%Y%m}-{uuid.uuid4().hex[:8].upper()}'

    def save(self, *args, **kwargs):
        if not self.codigo_unico:
            self.codigo_unico = self.generar_codigo_unico()
        super().save(*args, **kwargs)


class Validacion(models.Model):
    ESTADO_CHOICES = [
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    evidencia = models.ForeignKey(Evidencia, on_delete=models.CASCADE, related_name='validaciones')
    verificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='validaciones')
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    comentario = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Validación'
        verbose_name_plural = 'Validaciones'

    def __str__(self):
        return f'{self.evidencia.codigo_unico} - {self.estado}'
