from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .soft_delete import ActivosManager, SoftDeleteQuerySet


class TimeStampedModel(models.Model):
    """Fechas de auditoría: cuándo se creó y cuándo se modificó por última vez el registro.

    Quién hizo cada cambio y qué valores cambió queda en la traza de auditoría (colaboracion.AuditLog).
    """
    created_at = models.DateTimeField('creado el', auto_now_add=True)
    updated_at = models.DateTimeField('modificado el', auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # save(update_fields=[...]) escribe solo esos campos: sin agregarlo, updated_at no cambiaría.
        campos = kwargs.get('update_fields')
        if campos is not None:
            kwargs['update_fields'] = {*campos, 'updated_at'}
        super().save(*args, **kwargs)


class BaseModel(TimeStampedModel):
    """Base de las entidades de negocio (U2 · Clase 2): created_at, updated_at y deleted_at.

    deleted_at implementa el borrado lógico:
    - `objects` devuelve solo registros activos: es el que usan vistas, listados y exportaciones.
    - `all_objects` (manager por defecto) ve todo. Django lo usa para validar campos únicos,
      así un valor ocupado por un registro eliminado no provoca un IntegrityError.
    - `delete()` marca `deleted_at` en vez de borrar la fila; `hard_delete()` borra de verdad.
    """
    deleted_at = models.DateTimeField('eliminado el', null=True, blank=True, editable=False, db_index=True)

    # El primer manager declarado es el manager por defecto.
    all_objects = models.Manager.from_queryset(SoftDeleteQuerySet)()
    objects = ActivosManager()

    # related_name de los hijos que se eliminan lógicamente junto con este registro.
    soft_delete_cascade = ()

    class Meta:
        abstract = True

    def clean(self):
        # Ningún registro nuevo puede colgar de algo bloqueado (p. ej. una evidencia en un período cerrado).
        from .admin_utils import motivo_no_modificable

        motivo = motivo_no_modificable(self)
        if motivo:
            bloqueo = type(self).bloqueo_modificacion
            campo = next(iter(bloqueo[0])).split('__')[0]
            raise ValidationError({campo: motivo})

    def soft_delete(self, momento=None):
        if self.deleted_at is not None:
            return
        # Toda la cascada usa el mismo instante: así restore() sabe qué hijos cayeron con el padre.
        self.deleted_at = momento or timezone.now()
        self.save(update_fields=['deleted_at'])
        for relacion in self.soft_delete_cascade:
            for hijo in getattr(self, relacion).filter(deleted_at__isnull=True):
                hijo.soft_delete(self.deleted_at)

    def padre_eliminado(self):
        """El registro del que cuelga este y que sigue eliminado (p. ej. la actividad de una evidencia), o None."""
        for campo in self._meta.concrete_fields:
            padre = campo.related_model if campo.many_to_one else None
            valor = getattr(self, campo.attname) if padre else None
            if valor is not None and issubclass(padre, BaseModel):
                eliminado = padre.all_objects.filter(pk=valor, deleted_at__isnull=False).first()
                if eliminado is not None:
                    return eliminado
        return None

    def restore(self):
        """Recupera el registro y los hijos que se eliminaron junto con él (no los que ya estaban eliminados).

        Si el padre sigue eliminado no se restaura: el registro quedaría activo colgando de algo que nadie ve.
        """
        padre = self.padre_eliminado()
        if padre is not None:
            raise ValidationError(
                f'Restaure primero el registro de {padre._meta.verbose_name.lower()} «{padre}», que sigue eliminado.'
            )
        momento = self.deleted_at
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])
        if momento is None:
            return
        for relacion in self.soft_delete_cascade:
            for hijo in getattr(self, relacion).filter(deleted_at=momento):
                hijo.restore()

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


def es_soft_delete(model):
    return issubclass(model, BaseModel)


class Delegation(TimeStampedModel):
    name = models.CharField('nombre', max_length=120, unique=True)
    address = models.CharField('dirección', max_length=200)
    phone = models.CharField('teléfono', max_length=30, blank=True)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        db_table = 'delegation'
        ordering = ['name']
        verbose_name = 'Delegación'
        verbose_name_plural = 'Delegaciones'

    def __str__(self):
        return self.name


class Position(TimeStampedModel):
    name = models.CharField('nombre', max_length=120, unique=True)
    area = models.CharField('área', max_length=120, blank=True)
    description = models.TextField('descripción', blank=True)

    class Meta:
        db_table = 'position'
        ordering = ['name']
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'

    def __str__(self):
        return self.name


class ActivityType(TimeStampedModel):
    CATEGORY_CHOICES = [
        ('service', 'Atención'),
        ('paperwork', 'Tramitación'),
        ('field_work', 'Operativo'),
        ('social', 'Atención social'),
    ]

    code = models.CharField('código', max_length=20, unique=True)
    name = models.CharField('nombre', max_length=150)
    category = models.CharField('categoría', max_length=20, choices=CATEGORY_CHOICES)
    subtype = models.CharField('subtipo', max_length=120, blank=True)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        db_table = 'activity_type'
        ordering = ['code']
        verbose_name = 'Tipo de actividad'
        verbose_name_plural = 'Tipos de actividad'

    def __str__(self):
        return f'{self.code} - {self.name}'


class Period(TimeStampedModel):
    name = models.CharField('nombre', max_length=120, unique=True)
    start_date = models.DateField('fecha de inicio')
    end_date = models.DateField('fecha de término')
    is_closed = models.BooleanField('cerrado', default=False)
    min_threshold = models.DecimalField('umbral mínimo', max_digits=5, decimal_places=2, default=80.00)
    # RN-005: % máximo computable por ítem. 100 = nadie supera el 100 % (configurable por período).
    max_cap = models.DecimalField('tope máximo', max_digits=5, decimal_places=2, default=100.00)

    class Meta:
        db_table = 'period'
        ordering = ['-start_date']
        verbose_name = 'Período'
        verbose_name_plural = 'Períodos'

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError({'end_date': 'La fecha de inicio debe ser anterior a la fecha de término.'})
        if self.start_date and self.end_date:
            solapados = Period.objects.filter(
                start_date__lte=self.end_date,
                end_date__gte=self.start_date,
            ).exclude(pk=self.pk)
            if solapados.exists():
                raise ValidationError('El período se solapa con otro período ya existente.')


class Parameter(TimeStampedModel):
    key = models.CharField('clave', max_length=60, unique=True)
    value = models.CharField('valor', max_length=120)
    description = models.TextField('descripción', blank=True)
    is_active = models.BooleanField('activo', default=True)

    class Meta:
        db_table = 'parameter'
        ordering = ['key']
        verbose_name = 'Parámetro'
        verbose_name_plural = 'Parámetros'

    def __str__(self):
        return f'{self.key} = {self.value}'
