from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import Delegation, Period, ActivityType
from core.soft_delete import SoftDeleteModel
from funcionarios.models import Employee


class Activity(SoftDeleteModel):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ]

    number = models.CharField('número', max_length=30, unique=True)
    employee = models.ForeignKey(Employee, verbose_name='funcionario', on_delete=models.PROTECT, related_name='activities')
    delegation = models.ForeignKey(Delegation, verbose_name='delegación', on_delete=models.PROTECT, related_name='activities')
    period = models.ForeignKey(Period, verbose_name='período', on_delete=models.PROTECT, related_name='activities', null=True, blank=True)
    activity_type = models.ForeignKey(ActivityType, verbose_name='tipo de actividad', on_delete=models.PROTECT, related_name='activities')
    date = models.DateField('fecha')
    description = models.TextField('descripción')
    action = models.CharField('acción', max_length=200, blank=True)
    contact = models.CharField('contacto', max_length=150, blank=True)
    phone = models.CharField('teléfono', max_length=30, blank=True)
    is_agenda_item = models.BooleanField('indicador de agenda', default=False)
    evidence_code = models.CharField('código de evidencia', max_length=40, unique=True)
    validation_status = models.CharField('estado de validación', max_length=20, choices=STATUS_CHOICES, default='pending')

    soft_delete_cascade = ('evidence_items', 'social_cases')

    class Meta:
        db_table = 'activity'
        ordering = ['-date']
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'

    def __str__(self):
        return self.number

    def clean(self):
        # evidence_code es obligatorio por el propio campo (blank=False); no se repite aquí.
        if self.pk:
            original = Activity.all_objects.filter(pk=self.pk).values('period_id', 'period__is_closed').first()
            if original and original['period__is_closed'] and original['period_id'] != self.period_id:
                raise ValidationError({'period': 'La actividad pertenece a un período cerrado: no se puede cambiar de período.'})
        if self.period_id and self.period.is_closed:
            raise ValidationError({'period': 'Período cerrado: no se pueden registrar actividades.'})
        if self.employee_id and self.delegation_id and self.employee.delegation_id != self.delegation_id:
            raise ValidationError('La delegación debe coincidir con la delegación del funcionario.')


class SocialCase(SoftDeleteModel):
    activity = models.ForeignKey(
        Activity, verbose_name='actividad', on_delete=models.CASCADE, related_name='social_cases', limit_choices_to={'deleted_at__isnull': True},
    )
    step_number = models.PositiveSmallIntegerField(
        'número de gestión', validators=[MinValueValidator(1), MaxValueValidator(3)],
    )
    description = models.TextField('descripción')

    class Meta:
        db_table = 'social_case'
        ordering = ['activity', 'step_number']
        verbose_name = 'Atención social'
        verbose_name_plural = 'Atenciones sociales'
        constraints = [
            models.UniqueConstraint(fields=['activity', 'step_number'], name='unique_step_per_activity')
        ]

    def __str__(self):
        return f'{self.activity.number} - Gestión {self.step_number}'

    def clean(self):
        if self.activity_id and self.activity.activity_type.category != 'social':
            raise ValidationError({'activity': 'Solo las actividades de tipo "Atención social" admiten gestiones.'})
        if self.activity_id:
            existentes = SocialCase.objects.filter(activity=self.activity).exclude(pk=self.pk).count()
            if existentes >= 3:
                raise ValidationError('Una actividad no puede tener más de 3 gestiones de atención social.')
