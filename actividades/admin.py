from django.contrib import admin

from core.admin_utils import ScopedModelAdmin, es_usuario_sin_restriccion
from evidencias.models import Evidence

from .forms import ActividadForm
from .models import Activity, SocialCase


class EvidenciaInline(admin.TabularInline):
    model = Evidence
    extra = 0
    readonly_fields = ('unique_code', 'registered_at')
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).filter(deleted_at__isnull=True)


@admin.register(Activity)
class ActividadAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegation'
    form = ActividadForm
    list_display = ('number', 'employee', 'delegation', 'date', 'activity_type', 'validation_status')
    search_fields = ('number', 'employee__name', 'contact', 'evidence_code', 'description')
    list_filter = ('delegation', 'validation_status', 'period', 'date')
    ordering = ('-date',)
    list_select_related = ('employee', 'delegation', 'activity_type', 'period')
    autocomplete_fields = ('employee', 'activity_type')
    inlines = [EvidenciaInline]

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if not es_usuario_sin_restriccion(request.user) and 'validation_status' not in campos:
            campos.append('validation_status')
        return campos


@admin.register(SocialCase)
class AtencionSocialAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'activity__delegation'
    list_display = ('activity', 'step_number', 'description')
    search_fields = ('activity__number', 'description')
    list_filter = ('step_number',)
    ordering = ('activity', 'step_number')
    list_select_related = ('activity',)
