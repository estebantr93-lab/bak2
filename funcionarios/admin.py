from django.contrib import admin

from core.admin_utils import ScopedModelAdmin, es_usuario_sin_restriccion

from .models import Funcionario


@admin.register(Funcionario)
class FuncionarioAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegacion'
    list_display = ('nombre', 'user', 'delegacion', 'cargo', 'activo')
    search_fields = ('nombre', 'user__username')
    list_filter = ('delegacion', 'cargo', 'activo')
    ordering = ('nombre',)
    list_select_related = ('user', 'delegacion', 'cargo')
    autocomplete_fields = ('user', 'delegacion', 'cargo')

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        # Un admin de delegación no puede reasignar usuarios ni mover funcionarios a otra delegación.
        if not es_usuario_sin_restriccion(request.user):
            campos += [campo for campo in ('user', 'delegacion') if campo not in campos]
        return campos
