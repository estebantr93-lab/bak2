from django.contrib import admin

from .models import DashboardPanel


@admin.register(DashboardPanel)
class TableroPanelAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'owner')
    search_fields = ('name',)
    list_filter = ('kind',)
    ordering = ('name',)
    list_select_related = ('owner',)
