from django.core.exceptions import ValidationError
from django.db import models


class Delegacion(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=30, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Delegación'
        verbose_name_plural = 'Delegaciones'

    def __str__(self):
        return self.nombre


class Cargo(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    area = models.CharField(max_length=120, blank=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Cargo'
        verbose_name_plural = 'Cargos'

    def __str__(self):
        return self.nombre


class TipoActividad(models.Model):
    CATEGORIA_CHOICES = [
        ('atencion', 'Atención'),
        ('tramitacion', 'Tramitación'),
        ('operativo', 'Operativo'),
        ('social', 'Atención social'),
    ]

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    subtipo = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['codigo']
        verbose_name = 'Tipo de actividad'
        verbose_name_plural = 'Tipos de actividad'

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class Periodo(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    cerrado = models.BooleanField(default=False)
    umbral_minimo = models.DecimalField(max_digits=5, decimal_places=2, default=80.00)
    tope_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=150.00)

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Período'
        verbose_name_plural = 'Períodos'

    def __str__(self):
        return self.nombre

    def clean(self):
        if self.fecha_inicio and self.fecha_termino and self.fecha_inicio >= self.fecha_termino:
            raise ValidationError('La fecha de inicio debe ser anterior a la fecha de término.')
        if self.fecha_inicio and self.fecha_termino:
            solapados = Periodo.objects.filter(
                fecha_inicio__lte=self.fecha_termino,
                fecha_termino__gte=self.fecha_inicio,
            ).exclude(pk=self.pk)
            if solapados.exists():
                raise ValidationError('El período se solapa con otro período ya existente.')


class Parametro(models.Model):
    clave = models.CharField(max_length=60, unique=True)
    valor = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ['clave']
        verbose_name = 'Parámetro'
        verbose_name_plural = 'Parámetros'

    def __str__(self):
        return f'{self.clave} = {self.valor}'
