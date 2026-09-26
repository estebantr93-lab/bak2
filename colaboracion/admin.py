from django.contrib import admin

from .models import Alerta, Comentario, TrazaAuditoria


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('autor', 'content_type', 'object_id', 'fecha')
    search_fields = ('texto', 'autor__username')
    list_filter = ('content_type', 'fecha')
    ordering = ('-fecha',)
    list_select_related = ('autor', 'content_type')


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'texto', 'fecha', 'leida')
    search_fields = ('texto', 'destinatario__username')
    list_filter = ('leida',)
    ordering = ('-fecha',)
    list_select_related = ('destinatario',)


@admin.register(TrazaAuditoria)
class TrazaAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'accion', 'entidad_tipo', 'entidad_id', 'fecha')
    search_fields = ('accion', 'entidad_tipo', 'usuario__username')
    list_filter = ('accion', 'fecha')
    ordering = ('-fecha',)
    list_select_related = ('usuario',)
