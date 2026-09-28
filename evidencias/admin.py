from django.contrib import admin, messages

from core.admin_utils import ScopedModelAdmin, excluir_bloqueados

from .models import Evidence, Validation
from .services import ESTADOS_REVISION, registrar_revision


@admin.register(Evidence)
class EvidenciaAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'activity__delegation'
    list_display = ('unique_code', 'activity', 'status', 'registered_at', 'reviewed_by')
    search_fields = ('unique_code', 'activity__number')
    list_filter = ('status', 'activity__delegation')
    ordering = ('-registered_at',)
    list_select_related = ('activity', 'activity__delegation', 'reviewed_by')
    autocomplete_fields = ('activity',)
    actions = ['aprobar_evidencias']

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if obj is not None and 'unique_code' not in campos:
            campos.append('unique_code')
        if 'reviewed_by' not in campos:
            campos.append('reviewed_by')  # lo fija la acción de aprobar / la revisión del verificador
        return campos

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm('evidencias.can_approve_evidence'):
            actions.pop('aprobar_evidencias', None)
        return actions

    def aprobar_evidencias(self, request, queryset):
        if not request.user.has_perm('evidencias.can_approve_evidence'):
            self.message_user(request, 'No tiene permiso para aprobar evidencias.', level=messages.ERROR)
            return
        pendientes = queryset.exclude(status='approved')
        revisables = excluir_bloqueados(pendientes)  # las de un período cerrado no se tocan
        for evidencia in revisables:
            registrar_revision(evidencia, request.user, 'approved', 'Aprobada mediante acción masiva del Admin.')
        omitidas = pendientes.count() - revisables.count()
        self.message_user(request, f'{revisables.count()} evidencia(s) aprobada(s) correctamente.', level=messages.SUCCESS)
        if omitidas:
            self.message_user(request, f'{omitidas} evidencia(s) omitida(s) por pertenecer a un período cerrado.',
                              level=messages.WARNING)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change and 'status' in form.changed_data and obj.status in ESTADOS_REVISION:
            registrar_revision(obj, request.user, obj.status, obj.result or 'Revisión desde el Admin.')

    aprobar_evidencias.short_description = 'Aprobar evidencias seleccionadas'


@admin.register(Validation)
class ValidacionAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'evidence__activity__delegation'
    list_display = ('evidence', 'reviewer', 'status', 'date')
    search_fields = ('evidence__unique_code',)
    list_filter = ('status',)
    ordering = ('-date',)
    list_select_related = ('evidence', 'reviewer')
    readonly_fields = ('reviewer',)

    def save_model(self, request, obj, form, change):
        # Registrar una validación es revisar la evidencia: mismo servicio que el resto de las vías.
        registrar_revision(obj.evidence, request.user, obj.status, obj.comment, validacion=obj)

    def has_change_permission(self, request, obj=None):
        # Una validación es un registro de auditoría: se consulta, no se edita.
        return obj is None and super().has_change_permission(request, obj)
