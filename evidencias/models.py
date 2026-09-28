import os
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from actividades.models import Activity
from core.soft_delete import SoftDeleteModel

EXTENSIONES_IMAGEN = {'.jpg', '.jpeg', '.png'}


def ruta_evidencia(instance, filename):
    """No se confía en el nombre enviado: se conserva solo la extensión y se genera un nombre único."""
    extension = os.path.splitext(filename)[1].lower()
    return f'evidencias/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}'


class Evidence(SoftDeleteModel):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ]

    unique_code = models.CharField('código único', max_length=40, unique=True, blank=True)
    activity = models.ForeignKey(
        Activity, verbose_name='actividad', on_delete=models.CASCADE, related_name='evidence_items', limit_choices_to={'deleted_at__isnull': True},
    )
    description = models.TextField('descripción', blank=True)
    file = models.FileField('archivo', upload_to=ruta_evidencia, blank=True, null=True)
    registered_at = models.DateTimeField('fecha de registro', auto_now_add=True)
    status = models.CharField('estado', max_length=20, choices=STATUS_CHOICES, default='pending')
    result = models.CharField('resultado', max_length=200, blank=True)
    reviewed_by = models.ForeignKey(
        User, verbose_name='revisada por', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_evidence'
    )

    soft_delete_cascade = ('validations',)
    owner_field = 'activity__employee'
    bloqueo_modificacion = ({'activity__period__is_closed': True}, 'La actividad es de un período cerrado: no se puede modificar.')

    class Meta:
        db_table = 'evidence'
        ordering = ['-registered_at']
        verbose_name = 'Evidencia'
        verbose_name_plural = 'Evidencias'
        permissions = [
            ('can_approve_evidence', 'Puede aprobar evidencias'),
        ]

    def __str__(self):
        return self.unique_code

    @property
    def es_imagen(self):
        return bool(self.file) and os.path.splitext(self.file.name)[1].lower() in EXTENSIONES_IMAGEN

    @property
    def archivo_disponible(self):
        """False si la evidencia apunta a un archivo que ya no está en el servidor (enlace roto)."""
        return bool(self.file) and self.file.storage.exists(self.file.name)

    @staticmethod
    def generar_codigo_unico():
        return f'EVI-{timezone.now():%Y%m}-{uuid.uuid4().hex[:8].upper()}'

    def save(self, *args, **kwargs):
        if not self.unique_code:
            self.unique_code = self.generar_codigo_unico()
        super().save(*args, **kwargs)


class Validation(SoftDeleteModel):
    STATUS_CHOICES = [
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ]

    evidence = models.ForeignKey(
        Evidence, verbose_name='evidencia', on_delete=models.CASCADE, related_name='validations', limit_choices_to={'deleted_at__isnull': True},
    )
    reviewer = models.ForeignKey(User, verbose_name='verificador', on_delete=models.PROTECT, related_name='validations')
    date = models.DateTimeField('fecha', auto_now_add=True)
    status = models.CharField('estado', max_length=20, choices=STATUS_CHOICES)
    comment = models.TextField('comentario', blank=True)


    bloqueo_modificacion = ({'evidence__activity__period__is_closed': True}, 'La actividad es de un período cerrado: no se puede modificar.')
    class Meta:
        db_table = 'validation'
        ordering = ['-date']
        verbose_name = 'Validación'
        verbose_name_plural = 'Validaciones'

    def __str__(self):
        return f'{self.evidence.unique_code} - {self.status}'
