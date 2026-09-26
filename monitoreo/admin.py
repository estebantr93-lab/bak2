from django.contrib import admin

from .models import TableroPanel


@admin.register(TableroPanel)
class TableroPanelAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'propietario')
    search_fields = ('nombre',)
    list_filter = ('tipo',)
    ordering = ('nombre',)
    list_select_related = ('propietario',)
