from django.contrib import admin

from core.admin_utils import ScopedModelAdmin, es_usuario_sin_restriccion

from .models import PasswordResetCode, Employee


@admin.register(Employee)
class FuncionarioAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegation'
    list_display = ('name', 'user', 'delegation', 'position', 'is_active')
    search_fields = ('name', 'user__username')
    list_filter = ('delegation', 'position', 'is_active')
    ordering = ('name',)
    list_select_related = ('user', 'delegation', 'position')
    autocomplete_fields = ('user', 'delegation', 'position')

    def has_delete_permission(self, request, obj=None):
        # Un funcionario con historial no se borra: se desactiva con is_active (equivalente a borrado lógico).
        return False

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
