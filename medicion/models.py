from django.core.exceptions import ValidationError
from django.db import models

from core.models import Position, Delegation, Period, ActivityType
from funcionarios.models import Employee


class Goal(models.Model):
    position = models.ForeignKey(Position, verbose_name='cargo', on_delete=models.CASCADE, related_name='goals')
    period = models.ForeignKey(Period, verbose_name='período', on_delete=models.CASCADE, related_name='goals')
    activity_type = models.ForeignKey(ActivityType, verbose_name='tipo de actividad', on_delete=models.CASCADE, related_name='goals')
    target = models.PositiveIntegerField('meta')
    weight = models.DecimalField('ponderador', max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'goal'
        ordering = ['position', 'period']
        verbose_name = 'Meta'
        verbose_name_plural = 'Metas'
        constraints = [
            models.UniqueConstraint(
                fields=['position', 'period', 'activity_type'], name='unique_goal_position_period_type'
            )
        ]

    def __str__(self):
        return f'{self.position} - {self.period} - {self.activity_type}'

    def clean(self):
        errores = {}
        if self.weight is not None and self.weight <= 0:
            errores['weight'] = 'El ponderador debe ser mayor a 0.'
        if self.target is not None and self.target <= 0:
            errores['target'] = 'La meta debe ser mayor a 0.'
        if self.period_id and self.period.is_closed:
            # Cambiarlas reescribiría el cumplimiento de un período ya cerrado.
            errores['period'] = 'El período está cerrado: sus metas ya no se pueden modificar.'
        if errores:
            raise ValidationError(errores)


class Weighting(models.Model):
    position = models.ForeignKey(Position, verbose_name='cargo', on_delete=models.CASCADE, related_name='weightings')
    period = models.ForeignKey(Period, verbose_name='período', on_delete=models.CASCADE, related_name='weightings')
    detail = models.JSONField('detalle')
    generated_at = models.DateTimeField('fecha de generación', auto_now_add=True)

    class Meta:
        db_table = 'weighting'
        ordering = ['-generated_at']
        verbose_name = 'Ponderación'
        verbose_name_plural = 'Ponderaciones'

    def __str__(self):
        return f'{self.position} - {self.period} ({self.generated_at:%Y-%m-%d})'


class Indicator(models.Model):
    TRAFFIC_LIGHT_CHOICES = [
        ('green', 'Verde'),
        ('amber', 'Ámbar'),
        ('red', 'Rojo'),
    ]

    delegation = models.ForeignKey(
        Delegation, verbose_name='delegación', on_delete=models.CASCADE, related_name='indicators', null=True, blank=True
    )
    employee = models.ForeignKey(
        Employee, verbose_name='funcionario', on_delete=models.CASCADE, related_name='indicators', null=True, blank=True
    )
    position = models.ForeignKey(Position, verbose_name='cargo', on_delete=models.CASCADE, related_name='indicators', null=True, blank=True)
    period = models.ForeignKey(Period, verbose_name='período', on_delete=models.CASCADE, related_name='indicators')
    date = models.DateField('fecha')
    progress = models.PositiveIntegerField('avance')
    target = models.PositiveIntegerField('meta')
    compliance_pct = models.DecimalField('cumplimiento (%)', max_digits=6, decimal_places=2)
    traffic_light = models.CharField('semáforo', max_length=10, choices=TRAFFIC_LIGHT_CHOICES)

    class Meta:
        db_table = 'indicator'
        ordering = ['-date']
        verbose_name = 'Indicador'
        verbose_name_plural = 'Indicadores'

    def __str__(self):
        return f'{self.period} - {self.date} - {self.traffic_light}'

    def clean(self):
        if self.delegation_id is None and self.employee_id is None and self.position_id is None:
            raise ValidationError(
                'El indicador debe estar asociado a al menos una delegación, funcionario o cargo.'
            )
        duplicados = Indicator.objects.filter(
            delegation=self.delegation, employee=self.employee, position=self.position,
            period=self.period, date=self.date,
        ).exclude(pk=self.pk)
        if duplicados.exists():
            raise ValidationError(
                'Ya existe un indicador con la misma combinación de delegación/funcionario/cargo, período y fecha.'
            )
