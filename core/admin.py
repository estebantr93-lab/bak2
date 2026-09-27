from django.contrib import admin

from .admin_utils import ScopedModelAdmin

from .models import Position, Delegation, Parameter, Period, ActivityType

admin.site.site_header = 'SGR — Delegaciones Municipales de La Serena'
admin.site.site_title = 'Panel SGR'
admin.site.index_title = 'Administración del Sistema de Gestión de Resultados'


@admin.register(Delegation)
class DelegacionAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'pk'
    list_display = ('name', 'address', 'phone', 'is_active')
    search_fields = ('name', 'address')
    list_filter = ('is_active',)
    ordering = ('name',)


@admin.register(Position)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('name', 'area')
    search_fields = ('name', 'area')
    list_filter = ('area',)
    ordering = ('name',)


@admin.register(ActivityType)
class TipoActividadAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('category', 'is_active')
    ordering = ('code',)


@admin.register(Period)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_closed', 'min_threshold', 'max_cap')
    search_fields = ('name',)
    list_filter = ('is_closed',)
    ordering = ('-start_date',)


@admin.register(Parameter)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'is_active')
    search_fields = ('key', 'value')
    list_filter = ('is_active',)
    ordering = ('key',)
