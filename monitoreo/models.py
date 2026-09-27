from django.contrib.auth.models import User
from django.db import models


class DashboardPanel(models.Model):
    KIND_CHOICES = [
        ('personal', 'Personal'),
        ('delegation', 'Delegación'),
        ('global', 'Global'),
    ]

    name = models.CharField('nombre', max_length=150)
    kind = models.CharField('tipo', max_length=20, choices=KIND_CHOICES)
    parameters = models.JSONField('parámetros', default=dict, blank=True)
    owner = models.ForeignKey(
        User, verbose_name='propietario', on_delete=models.SET_NULL, null=True, blank=True, related_name='dashboard_panels'
    )

    class Meta:
        db_table = 'dashboard_panel'
        ordering = ['name']
        verbose_name = 'Tablero/Panel'
        verbose_name_plural = 'Tableros/Paneles'

    def __str__(self):
        return f'{self.name} ({self.get_kind_display()})'
