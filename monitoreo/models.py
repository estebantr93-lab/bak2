from django.contrib.auth.models import User
from django.db import models


class TableroPanel(models.Model):
    TIPO_CHOICES = [
        ('personal', 'Personal'),
        ('delegacion', 'Delegación'),
        ('global', 'Global'),
    ]

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    parametros = models.JSONField(default=dict, blank=True)
    propietario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tableros'
    )

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Tablero/Panel'
        verbose_name_plural = 'Tableros/Paneles'

    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_display()})'
