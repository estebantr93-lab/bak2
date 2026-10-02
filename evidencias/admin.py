from django.contrib import admin, messages

from core.admin_utils import FILTRO_MODIFICACION, ROL_VERIFICADOR, ScopedModelAdmin, excluir_bloqueados, get_rol

from .forms import CAMPOS_REVISION, EvidenciaAdminForm
from .models import Evidence, Validation
from .services import ESTADOS_REVISION, registrar_revision


@admin.register(Evidence)
class EvidenciaAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'activity__delegation'
    form = EvidenciaAdminForm  # mismas validaciones de archivo y de rechazo que la web
    list_display = ('unique_code', 'activity', 'status', 'registered_at', 'reviewed_by')
    search_fields = ('unique_code', 'activity__number')
    list_filter = ('status', 'activity__delegation', 'registered_at', FILTRO_MODIFICACION)
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
        if obj is not None and get_rol(request.user) == ROL_VERIFICADOR:
            # El verificador revisa: no reasigna la evidencia ni reemplaza lo que cargó el funcionario.
            campos += [f.name for f in Evidence._meta.fields
                       if f.editable and f.name not in CAMPOS_REVISION and f.name not in campos]
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
        # Se materializa antes de aprobar: después ya no estarían "pendientes" y los conteos saldrían mal.
        revisables = list(excluir_bloqueados(pendientes))  # las de un período cerrado no se tocan
        omitidas = pendientes.count() - len(revisables)
        for evidencia in revisables:
            registrar_revision(evidencia, request.user, 'approved', 'Aprobada mediante acción masiva del Admin.')
        self.message_user(request, f'{len(revisables)} evidencia(s) aprobada(s) correctamente.', level=messages.SUCCESS)
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
    list_filter = ('status', 'date')
    ordering = ('-date',)
    list_select_related = ('evidence', 'reviewer')
    readonly_fields = ('reviewer',)

    def save_model(self, request, obj, form, change):
        # Registrar una validación es revisar la evidencia: mismo servicio que el resto de las vías.
        registrar_revision(obj.evidence, request.user, obj.status, obj.comment, validacion=obj)

    def has_change_permission(self, request, obj=None):
        # Una validación es un registro de auditoría: se consulta, no se edita.
        return obj is None and super().has_change_permission(request, obj)
