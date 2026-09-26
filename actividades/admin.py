from django.contrib import admin

from core.admin_utils import ScopedModelAdmin, es_usuario_sin_restriccion
from evidencias.models import Evidencia

from .forms import ActividadForm
from .models import Actividad, AtencionSocial


class EvidenciaInline(admin.TabularInline):
    model = Evidencia
    extra = 0
    readonly_fields = ('codigo_unico', 'fecha_registro')
    can_delete = False


@admin.register(Actividad)
class ActividadAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegacion'
    form = ActividadForm
    list_display = ('numero', 'funcionario', 'delegacion', 'fecha', 'tipo_actividad', 'estado_validacion')
    search_fields = ('numero', 'funcionario__nombre', 'contacto', 'codigo_evidencia', 'descripcion')
    list_filter = ('delegacion', 'estado_validacion', 'periodo', 'fecha')
    ordering = ('-fecha',)
    list_select_related = ('funcionario', 'delegacion', 'tipo_actividad', 'periodo')
    autocomplete_fields = ('funcionario', 'tipo_actividad')
    inlines = [EvidenciaInline]

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if not es_usuario_sin_restriccion(request.user) and 'estado_validacion' not in campos:
            campos.append('estado_validacion')
        return campos


@admin.register(AtencionSocial)
class AtencionSocialAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'actividad__delegacion'
    list_display = ('actividad', 'numero_gestion', 'descripcion')
    search_fields = ('actividad__numero', 'descripcion')
    list_filter = ('numero_gestion',)
    ordering = ('actividad', 'numero_gestion')
    list_select_related = ('actividad',)
