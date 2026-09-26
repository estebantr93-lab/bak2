from django.contrib import admin

from .forms import PeriodoForm
from .models import Cargo, Delegacion, Parametro, Periodo, TipoActividad

admin.site.site_header = 'SGR — Delegaciones Municipales de La Serena'
admin.site.site_title = 'Panel SGR'
admin.site.index_title = 'Administración del Sistema de Gestión de Resultados'


@admin.register(Delegacion)
class DelegacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'telefono', 'activa')
    search_fields = ('nombre', 'direccion')
    list_filter = ('activa',)
    ordering = ('nombre',)


@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'area')
    search_fields = ('nombre', 'area')
    list_filter = ('area',)
    ordering = ('nombre',)


@admin.register(TipoActividad)
class TipoActividadAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria', 'activo')
    search_fields = ('codigo', 'nombre')
    list_filter = ('categoria', 'activo')
    ordering = ('codigo',)


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    form = PeriodoForm
    list_display = ('nombre', 'fecha_inicio', 'fecha_termino', 'cerrado', 'umbral_minimo', 'tope_maximo')
    search_fields = ('nombre',)
    list_filter = ('cerrado',)
    ordering = ('-fecha_inicio',)


@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ('clave', 'valor', 'vigente')
    search_fields = ('clave', 'valor')
    list_filter = ('vigente',)
    ordering = ('clave',)
