from django.contrib import admin

from core.admin_utils import ScopedModelAdmin
from evidencias.forms import EvidenciaAdminForm
from evidencias.models import Evidence

from .forms import ActividadForm
from .models import Activity, SocialCase


class EvidenciaInline(admin.TabularInline):
    model = Evidence
    form = EvidenciaAdminForm  # valida tipo, tamaño y contenido del archivo, igual que la web
    extra = 0
    # El estado se cambia solo revisando (Evidencias o Validaciones), que registra revisor y Validation.
    readonly_fields = ('unique_code', 'registered_at', 'status', 'result', 'reviewed_by')
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

    # El estado de validación se deriva de las evidencias (evidencias/services.py): nadie lo edita a mano,
    # porque la siguiente revisión lo recalcularía de todas formas.
    readonly_fields = ('validation_status',)


@admin.register(SocialCase)
class AtencionSocialAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'activity__delegation'
    list_display = ('activity', 'step_number', 'description')
    search_fields = ('activity__number', 'description')
    list_filter = ('step_number',)
    ordering = ('activity', 'step_number')
    list_select_related = ('activity',)
