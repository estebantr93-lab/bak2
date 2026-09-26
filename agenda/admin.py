from django.contrib import admin

from core.admin_utils import ScopedModelAdmin

from .models import Compromiso, SeguimientoCompromiso


@admin.register(Compromiso)
class CompromisoAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegacion'
    list_display = ('titulo', 'delegacion', 'responsable', 'fecha_vencimiento', 'estado')
    search_fields = ('titulo', 'descripcion')
    list_filter = ('delegacion', 'estado')
    ordering = ('fecha_vencimiento',)
    list_select_related = ('delegacion', 'responsable')
    autocomplete_fields = ('responsable',)


@admin.register(SeguimientoCompromiso)
class SeguimientoCompromisoAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'compromiso__delegacion'
    list_display = ('compromiso', 'fecha', 'responsable', 'estado_nuevo')
    search_fields = ('compromiso__titulo',)
    list_filter = ('estado_nuevo',)
    ordering = ('-fecha',)
    list_select_related = ('compromiso', 'responsable')
