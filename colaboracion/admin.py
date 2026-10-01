from django.contrib import admin

from .models import Alert, Comment, AuditLog


@admin.register(Comment)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('author', 'content_type', 'object_id', 'date')
    search_fields = ('text', 'author__username')
    list_filter = ('content_type', 'date')
    ordering = ('-date',)
    list_select_related = ('author', 'content_type')


@admin.register(Alert)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'text', 'date', 'is_read')
    search_fields = ('text', 'recipient__username')
    list_filter = ('is_read',)
    ordering = ('-date',)
    list_select_related = ('recipient',)


@admin.register(AuditLog)
class TrazaAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'action', 'entity_type', 'entity_id', 'resumen_de_cambios')
    search_fields = ('action', 'entity_type', 'user__username', 'detail')
    list_filter = ('action', 'date')
    ordering = ('-date',)
    list_select_related = ('user',)

    @admin.display(description='cambios (antes → después)')
    def resumen_de_cambios(self, obj):
        partes = [f'{campo}: {antes or "—"} → {despues or "—"}' for campo, (antes, despues) in (obj.changes or {}).items()]
        return '; '.join(partes) or '—'

    # Es una traza de auditoría: se consulta, no se crea, edita ni borra a mano.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
