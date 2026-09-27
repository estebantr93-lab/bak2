from django.contrib import admin, messages

from core.admin_utils import ScopedModelAdmin

from .models import Evidence, Validation


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
        aprobadas = 0
        for evidencia in queryset.exclude(status='approved'):
            evidencia.status = 'approved'
            evidencia.reviewed_by = request.user
            evidencia.save()
            Validation.objects.create(
                evidence=evidencia,
                reviewer=request.user,
                status='approved',
                comment='Aprobada mediante acción masiva del Admin.',
            )
            aprobadas += 1
        self.message_user(request, f'{aprobadas} evidencia(s) aprobada(s) correctamente.', level=messages.SUCCESS)

    aprobar_evidencias.short_description = 'Aprobar evidencias seleccionadas'


@admin.register(Validation)
class ValidacionAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'evidence__activity__delegation'
    list_display = ('evidence', 'reviewer', 'status', 'date')
    search_fields = ('evidence__unique_code',)
    list_filter = ('status',)
    ordering = ('-date',)
    list_select_related = ('evidence', 'reviewer')
