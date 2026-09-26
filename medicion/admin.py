from django.contrib import admin

from core.admin_utils import ScopedModelAdmin

from .forms import MetaForm
from .models import Indicador, Ponderacion
from .models import Meta as MetaModel


@admin.register(MetaModel)
class MetaAdmin(admin.ModelAdmin):
    form = MetaForm
    list_display = ('cargo', 'periodo', 'tipo_actividad', 'meta', 'ponderador')
    search_fields = ('cargo__nombre', 'tipo_actividad__nombre')
    list_filter = ('periodo', 'cargo')
    ordering = ('cargo', 'periodo')
    list_select_related = ('cargo', 'periodo', 'tipo_actividad')


@admin.register(Ponderacion)
class PonderacionAdmin(admin.ModelAdmin):
    list_display = ('cargo', 'periodo', 'fecha_generacion')
    search_fields = ('cargo__nombre',)
    list_filter = ('periodo',)
    ordering = ('-fecha_generacion',)
    list_select_related = ('cargo', 'periodo')


@admin.register(Indicador)
class IndicadorAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegacion'
    list_display = (
        'periodo', 'fecha', 'delegacion', 'funcionario', 'cargo', 'avance', 'meta', 'cumplimiento_pct', 'semaforo',
    )
    search_fields = ('delegacion__nombre', 'funcionario__nombre')
    list_filter = ('semaforo', 'periodo', 'delegacion')
    ordering = ('-fecha',)
    list_select_related = ('delegacion', 'funcionario', 'cargo', 'periodo')
