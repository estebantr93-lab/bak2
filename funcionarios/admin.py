from django.contrib import admin
from django.core.exceptions import PermissionDenied

from core.admin_utils import FILTRO_MODIFICACION, ScopedModelAdmin, es_usuario_sin_restriccion

from .models import PasswordResetCode, Employee


@admin.register(Employee)
class FuncionarioAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegation'
    list_display = ('name', 'user', 'delegation', 'position', 'is_active')
    search_fields = ('name', 'user__username')
    list_filter = ('delegation', 'position', 'is_active', FILTRO_MODIFICACION)
    ordering = ('name',)
    list_select_related = ('user', 'delegation', 'position')
    autocomplete_fields = ('user', 'delegation', 'position')

    # Un funcionario se desactiva con is_active (equivalente a borrado lógico): se quitan las entradas de
    # borrado de este Admin, sin negar el permiso, para no bloquear la eliminación en cascada de un User.
    def get_actions(self, request):
        acciones = super().get_actions(request)
        acciones.pop('delete_selected', None)
        return acciones

    def delete_view(self, request, object_id, extra_context=None):
        raise PermissionDenied('Los funcionarios no se eliminan: desactívelos con el campo "activo".')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return super().change_view(request, object_id, form_url, {**(extra_context or {}), 'show_delete': False})

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        # Un admin de delegación no puede reasignar usuarios ni mover funcionarios a otra delegación.
        if not es_usuario_sin_restriccion(request.user):
            campos += [campo for campo in ('user', 'delegation') if campo not in campos]
        return campos


@admin.register(PasswordResetCode)
class CodigoRecuperacionAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'expires_at', 'attempts', 'is_used')
    list_filter = ('is_used',)
    search_fields = ('user__username', 'user__email')
    # El hash no se muestra ni se edita desde el Admin.
    exclude = ('code_hash',)
    readonly_fields = ('user', 'created_at', 'expires_at', 'attempts', 'is_used')

    def has_add_permission(self, request):
        return False
