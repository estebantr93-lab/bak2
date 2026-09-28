from django.core.exceptions import ValidationError
from django.db import models

from core.models import Delegation
from core.soft_delete import SoftDeleteModel
from funcionarios.models import Employee


class Commitment(SoftDeleteModel):
    STATUS_CHOICES = [
        ('registered', 'Ingresado'),
        ('pending', 'Pendiente'),
        ('in_progress', 'En proceso'),
        ('done', 'Realizado'),
    ]

    title = models.CharField('título', max_length=200)
    description = models.TextField('descripción', blank=True)
    delegation = models.ForeignKey(Delegation, verbose_name='delegación', on_delete=models.PROTECT, related_name='commitments')
    responsible = models.ForeignKey(
        Employee, verbose_name='responsable', on_delete=models.SET_NULL, null=True, blank=True, related_name='commitments'
    )
    due_date = models.DateField('fecha de vencimiento')
    status = models.CharField('estado', max_length=20, choices=STATUS_CHOICES, default='registered')
    notes = models.TextField('observaciones', blank=True)

    soft_delete_cascade = ('follow_ups',)
    owner_field = 'responsible'

    class Meta:
        db_table = 'commitment'
        ordering = ['due_date']
        verbose_name = 'Compromiso'
        verbose_name_plural = 'Compromisos'

    def __str__(self):
        return self.title

    def clean(self):
        if self.responsible_id and self.delegation_id and self.responsible.delegation_id != self.delegation_id:
            raise ValidationError({'responsible': 'El responsable debe pertenecer a la delegación del compromiso.'})
        if self.status == 'done' and not self.notes.strip():
            raise ValidationError({'notes': 'Para marcar el compromiso como realizado debe registrar observaciones.'})


class CommitmentFollowUp(SoftDeleteModel):
    commitment = models.ForeignKey(
        Commitment, verbose_name='compromiso', on_delete=models.CASCADE, related_name='follow_ups', limit_choices_to={'deleted_at__isnull': True},
    )
    date = models.DateTimeField('fecha', auto_now_add=True)
    responsible = models.ForeignKey(
        Employee, verbose_name='responsable', on_delete=models.SET_NULL, null=True, blank=True, related_name='follow_ups'
    )
    description = models.TextField('descripción')
    new_status = models.CharField('estado nuevo', max_length=20, choices=Commitment.STATUS_CHOICES)

    owner_field = 'commitment__responsible'

    class Meta:
        db_table = 'commitment_follow_up'
        ordering = ['-date']
        verbose_name = 'Seguimiento de compromiso'
        verbose_name_plural = 'Seguimientos de compromiso'

    def __str__(self):
        return f'{self.commitment.title} - {self.new_status}'

    def save(self, *args, **kwargs):
        nuevo = self._state.adding
        super().save(*args, **kwargs)
        if nuevo and self.deleted_at is None:
            # Un seguimiento registra el avance: el compromiso pasa al estado indicado. Si queda
            # realizado sin observaciones, la descripción del seguimiento sirve como tales.
            cambios = {'status': self.new_status}
            if self.new_status == 'done' and not self.commitment.notes.strip():
                cambios['notes'] = self.description
            Commitment.all_objects.filter(pk=self.commitment_id).update(**cambios)
