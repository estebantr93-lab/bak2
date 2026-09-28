import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import Delegation, Period, ActivityType
from core.soft_delete import SoftDeleteModel
from funcionarios.models import Employee


def sin_evidencia(qs):
    """Actividades sin ninguna evidencia activa, evaluado por actividad con una subconsulta EXISTS.

    No sirve filtrar por un conteo agregado (al agrupar después por funcionario la condición pasa al
    grupo) ni exclude(evidence_items__deleted_at__isnull=True) (una actividad sin evidencias también
    «cumple» isnull). Lo usan el dashboard y el filtro ?sin_evidencia=1 de la lista.
    """
    from evidencias.models import Evidence  # evidencias depende de actividades: import local

    activas = Evidence.objects.filter(activity=models.OuterRef('pk'))  # objects = solo no eliminadas
    return qs.filter(~models.Exists(activas))


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
    # RN-010 / RF-011: lo genera el sistema al registrar la actividad y no cambia nunca (ver save() y clean()).
    evidence_code = models.CharField('código de evidencia', max_length=40, unique=True, blank=True)
    validation_status = models.CharField('estado de validación', max_length=20, choices=STATUS_CHOICES, default='pending')

    soft_delete_cascade = ('evidence_items', 'social_cases')
    owner_field = 'employee'  # el rol funcionario solo modifica sus propias actividades
    # Lo registrado en un período cerrado queda congelado (web y Admin, también sus evidencias y gestiones).
    bloqueo_modificacion = ({'period__is_closed': True}, 'Actividad de un período cerrado: no se puede modificar ni eliminar.')
    # Una vez aprobada, el funcionario ya no la cambia (la aprobación quedaría respaldando otro contenido);
    # un administrador sí puede corregirla. Lo aplica core/admin_utils.modificables.
    bloqueo_funcionario = ({'validation_status': 'approved'}, 'La actividad ya fue aprobada: solo un administrador puede modificarla.')

    class Meta:
        db_table = 'activity'
        ordering = ['-date']
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'

    def __str__(self):
        return self.number

    @staticmethod
    def generar_codigo_evidencia():
        return f'EV-{timezone.now():%Y%m}-{uuid.uuid4().hex[:8].upper()}'

    def save(self, *args, **kwargs):
        if not self.evidence_code:
            self.evidence_code = self.generar_codigo_evidencia()
        super().save(*args, **kwargs)

    def clean(self):
        if self.pk:
            codigo = Activity.all_objects.filter(pk=self.pk).values_list('evidence_code', flat=True).first()
            if codigo and self.evidence_code != codigo:
                raise ValidationError({'evidence_code': 'El código de evidencia es inmutable: no se puede cambiar.'})
            original = Activity.all_objects.filter(pk=self.pk).values('period_id', 'period__is_closed').first()
            if original and original['period__is_closed'] and original['period_id'] != self.period_id:
                raise ValidationError({'period': 'La actividad pertenece a un período cerrado: no se puede cambiar de período.'})
        if self.period_id and self.period.is_closed:
            raise ValidationError({'period': 'Período cerrado: no se pueden registrar actividades.'})
        if self.date and self.date > timezone.localdate():
            raise ValidationError({'date': 'La fecha no puede ser futura: se registran actividades ya realizadas.'})
        if self.date and self.period_id and not (self.period.start_date <= self.date <= self.period.end_date):
            raise ValidationError({'date': (
                f'La fecha debe estar dentro del período {self.period} '
                f'({self.period.start_date:%d-%m-%Y} a {self.period.end_date:%d-%m-%Y}).'
            )})
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
    # RN-012: cada gestión conserva su fecha y su resultado.
    date = models.DateField('fecha de la gestión', default=timezone.localdate)
    result = models.CharField('resultado', max_length=200, blank=True)

    owner_field = 'activity__employee'
    bloqueo_modificacion = ({'activity__period__is_closed': True}, 'La actividad es de un período cerrado: no se puede modificar.')
    # Aprobada la actividad, el funcionario tampoco cambia sus gestiones (mismo criterio que la actividad).
    bloqueo_funcionario = ({'activity__validation_status': 'approved'}, 'La actividad ya fue aprobada: solo un administrador puede modificar sus gestiones.')

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
        super().clean()
        if self.activity_id and self.activity.activity_type.category != 'social':
            raise ValidationError({'activity': 'Solo las actividades de tipo "Atención social" admiten gestiones.'})
        if self.activity_id:
            if self.date and self.activity.date and self.date < self.activity.date:
                raise ValidationError({'date': 'La gestión no puede ser anterior a la actividad.'})
            if self.date and self.date > timezone.localdate():
                raise ValidationError({'date': 'La fecha de la gestión no puede ser futura.'})
            existentes = SocialCase.objects.filter(activity=self.activity).exclude(pk=self.pk).count()
            if existentes >= 3:
                raise ValidationError('Una actividad no puede tener más de 3 gestiones de atención social.')
