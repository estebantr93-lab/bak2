from django.core.exceptions import ValidationError
from django.db import models


class Delegation(models.Model):
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


class Position(models.Model):
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


class ActivityType(models.Model):
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


class Period(models.Model):
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


class Parameter(models.Model):
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
