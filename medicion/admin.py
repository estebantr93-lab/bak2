from django.contrib import admin

from django.contrib import messages

from core.admin_utils import AuditarCambiosAdmin, ScopedModelAdmin

from .forms import GoalForm
from .services import SUMA_PONDERADORES, formato_numero, suma_ponderadores
from .models import Indicator, Weighting
from .models import Goal


@admin.register(Goal)
class GoalAdmin(AuditarCambiosAdmin, admin.ModelAdmin):
    form = GoalForm
    list_display = ('position', 'period', 'activity_type', 'target', 'weight', 'suma_del_cargo')

    @admin.display(description='Suma del cargo (RN-001)')
    def suma_del_cargo(self, obj):
        suma = suma_ponderadores(Goal.objects.filter(position=obj.position, period=obj.period))
        return f'{formato_numero(suma)} %' + ('' if suma == SUMA_PONDERADORES else ' · incompleta')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # RN-001: las metas se cargan de a una; mientras la suma no sea 100 % se avisa y el dashboard
        # no calcula el cumplimiento de ese cargo.
        suma = suma_ponderadores(Goal.objects.filter(position=obj.position, period=obj.period))
        if suma != SUMA_PONDERADORES:
            self.message_user(request, (
                f'Los ponderadores de {obj.position} en {obj.period} suman {formato_numero(suma)} %: deben sumar 100 %. '
                'Hasta completarlos, el dashboard no calcula el cumplimiento de ese cargo.'
            ), level=messages.WARNING)
    search_fields = ('position__name', 'activity_type__name')
    list_filter = ('period', 'position')
    ordering = ('position', 'period')
    list_select_related = ('position', 'period', 'activity_type')


@admin.register(Weighting)
class PonderacionAdmin(AuditarCambiosAdmin, admin.ModelAdmin):
    list_display = ('position', 'period', 'generated_at')
    search_fields = ('position__name',)
    list_filter = ('period',)
    ordering = ('-generated_at',)
    list_select_related = ('position', 'period')


@admin.register(Indicator)
class IndicadorAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegation'
    list_display = (
        'period', 'date', 'delegation', 'employee', 'position', 'progress', 'target', 'compliance_pct', 'traffic_light',
    )
    search_fields = ('delegation__name', 'employee__name')
    list_filter = ('traffic_light', 'period', 'delegation')
    ordering = ('-date',)
    list_select_related = ('delegation', 'employee', 'position', 'period')
