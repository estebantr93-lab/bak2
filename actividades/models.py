from django.core.exceptions import ValidationError
from django.db import models

from core.models import Delegacion, Periodo, TipoActividad
from funcionarios.models import Funcionario


class Actividad(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    ]

    numero = models.CharField(max_length=30, unique=True)
    funcionario = models.ForeignKey(Funcionario, on_delete=models.PROTECT, related_name='actividades')
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name='actividades')
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT, related_name='actividades', null=True, blank=True)
    tipo_actividad = models.ForeignKey(TipoActividad, on_delete=models.PROTECT, related_name='actividades')
    fecha = models.DateField()
    descripcion = models.TextField()
    accion = models.CharField(max_length=200, blank=True)
    contacto = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    indicador_agenda = models.BooleanField(default=False)
    codigo_evidencia = models.CharField(max_length=40, unique=True)
    estado_validacion = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'

    def __str__(self):
        return self.numero

    def clean(self):
        if self.periodo_id and self.periodo.cerrado:
            raise ValidationError('Período cerrado: no se pueden registrar actividades.')
        if not self.codigo_evidencia:
            raise ValidationError('El código de evidencia es obligatorio.')
        if self.funcionario_id and self.delegacion_id and self.funcionario.delegacion_id != self.delegacion_id:
            raise ValidationError('La delegación debe coincidir con la delegación del funcionario.')


class AtencionSocial(models.Model):
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='atenciones_sociales')
    numero_gestion = models.PositiveSmallIntegerField()
    descripcion = models.TextField()

    class Meta:
        ordering = ['actividad', 'numero_gestion']
        verbose_name = 'Atención social'
        verbose_name_plural = 'Atenciones sociales'
        constraints = [
            models.UniqueConstraint(fields=['actividad', 'numero_gestion'], name='unique_gestion_por_actividad')
        ]

    def __str__(self):
        return f'{self.actividad.numero} - Gestión {self.numero_gestion}'

    def clean(self):
        if self.numero_gestion and (self.numero_gestion < 1 or self.numero_gestion > 3):
            raise ValidationError('El número de gestión debe estar entre 1 y 3.')
        if self.actividad_id:
            existentes = AtencionSocial.objects.filter(actividad=self.actividad).exclude(pk=self.pk).count()
            if existentes >= 3:
                raise ValidationError('Una actividad no puede tener más de 3 gestiones de atención social.')
