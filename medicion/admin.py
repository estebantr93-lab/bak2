from django.contrib import admin

from core.admin_utils import ScopedModelAdmin

from .forms import GoalForm
from .models import Indicator, Weighting
from .models import Goal


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    form = GoalForm
    list_display = ('position', 'period', 'activity_type', 'target', 'weight')
    search_fields = ('position__name', 'activity_type__name')
    list_filter = ('period', 'position')
    ordering = ('position', 'period')
    list_select_related = ('position', 'period', 'activity_type')


@admin.register(Weighting)
class PonderacionAdmin(admin.ModelAdmin):
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
