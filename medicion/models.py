from django.core.exceptions import ValidationError
from django.db import models

from core.models import Cargo, Delegacion, Periodo, TipoActividad
from funcionarios.models import Funcionario


class Meta(models.Model):
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, related_name='metas')
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='metas')
    tipo_actividad = models.ForeignKey(TipoActividad, on_delete=models.CASCADE, related_name='metas')
    meta = models.PositiveIntegerField()
    ponderador = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ['cargo', 'periodo']
        verbose_name = 'Meta'
        verbose_name_plural = 'Metas'
        constraints = [
            models.UniqueConstraint(
                fields=['cargo', 'periodo', 'tipo_actividad'], name='unique_meta_cargo_periodo_tipo'
            )
        ]

    def __str__(self):
        return f'{self.cargo} - {self.periodo} - {self.tipo_actividad}'

    def clean(self):
        if self.ponderador is not None and self.ponderador <= 0:
            raise ValidationError('El ponderador debe ser mayor a 0.')
        if self.meta is not None and self.meta <= 0:
            raise ValidationError('La meta debe ser mayor a 0.')


class Ponderacion(models.Model):
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, related_name='ponderaciones')
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='ponderaciones')
    detalle = models.JSONField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_generacion']
        verbose_name = 'Ponderación'
        verbose_name_plural = 'Ponderaciones'

    def __str__(self):
        return f'{self.cargo} - {self.periodo} ({self.fecha_generacion:%Y-%m-%d})'


class Indicador(models.Model):
    SEMAFORO_CHOICES = [
        ('verde', 'Verde'),
        ('ambar', 'Ámbar'),
        ('rojo', 'Rojo'),
    ]

    delegacion = models.ForeignKey(
        Delegacion, on_delete=models.CASCADE, related_name='indicadores', null=True, blank=True
    )
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name='indicadores', null=True, blank=True
    )
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE, related_name='indicadores', null=True, blank=True)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, related_name='indicadores')
    fecha = models.DateField()
    avance = models.PositiveIntegerField()
    meta = models.PositiveIntegerField()
    cumplimiento_pct = models.DecimalField(max_digits=6, decimal_places=2)
    semaforo = models.CharField(max_length=10, choices=SEMAFORO_CHOICES)

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Indicador'
        verbose_name_plural = 'Indicadores'

    def __str__(self):
        return f'{self.periodo} - {self.fecha} - {self.semaforo}'

    def clean(self):
        if self.delegacion_id is None and self.funcionario_id is None and self.cargo_id is None:
            raise ValidationError(
                'El indicador debe estar asociado a al menos una delegación, funcionario o cargo.'
            )
        duplicados = Indicador.objects.filter(
            delegacion=self.delegacion, funcionario=self.funcionario, cargo=self.cargo,
            periodo=self.periodo, fecha=self.fecha,
        ).exclude(pk=self.pk)
        if duplicados.exists():
            raise ValidationError(
                'Ya existe un indicador con la misma combinación de delegación/funcionario/cargo, período y fecha.'
            )
