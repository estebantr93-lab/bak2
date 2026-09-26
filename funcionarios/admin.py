from django.contrib import admin

from core.admin_utils import ScopedModelAdmin

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
