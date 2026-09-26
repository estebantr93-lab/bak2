from django.contrib import admin, messages

from core.admin_utils import ScopedModelAdmin

from .models import Evidencia, Validacion


@admin.register(Evidencia)
class EvidenciaAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'actividad__delegacion'
    list_display = ('codigo_unico', 'actividad', 'estado', 'fecha_registro', 'revisada_por')
    search_fields = ('codigo_unico', 'actividad__numero')
    list_filter = ('estado', 'actividad__delegacion')
    ordering = ('-fecha_registro',)
    list_select_related = ('actividad', 'actividad__delegacion', 'revisada_por')
    autocomplete_fields = ('actividad',)
    actions = ['aprobar_evidencias']

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if obj is not None and 'codigo_unico' not in campos:
            campos.append('codigo_unico')
        return campos

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm('evidencias.can_approve_evidencia'):
            actions.pop('aprobar_evidencias', None)
        return actions

    def aprobar_evidencias(self, request, queryset):
        if not request.user.has_perm('evidencias.can_approve_evidencia'):
            self.message_user(request, 'No tiene permiso para aprobar evidencias.', level=messages.ERROR)
            return
        aprobadas = 0
        for evidencia in queryset.exclude(estado='aprobada'):
            evidencia.estado = 'aprobada'
            evidencia.revisada_por = request.user
            evidencia.save()
            Validacion.objects.create(
                evidencia=evidencia,
                verificador=request.user,
                estado='aprobada',
                comentario='Aprobada mediante acción masiva del Admin.',
            )
            aprobadas += 1
        self.message_user(request, f'{aprobadas} evidencia(s) aprobada(s) correctamente.', level=messages.SUCCESS)

    aprobar_evidencias.short_description = 'Aprobar evidencias seleccionadas'


@admin.register(Validacion)
class ValidacionAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'evidencia__actividad__delegacion'
    list_display = ('evidencia', 'verificador', 'estado', 'fecha')
    search_fields = ('evidencia__codigo_unico',)
    list_filter = ('estado',)
    ordering = ('-fecha',)
    list_select_related = ('evidencia', 'verificador')
