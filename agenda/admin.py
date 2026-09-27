from django.contrib import admin

from core.admin_utils import ScopedModelAdmin

from .models import Commitment, CommitmentFollowUp


@admin.register(Commitment)
class CompromisoAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'delegation'
    list_display = ('title', 'delegation', 'responsible', 'due_date', 'status')
    search_fields = ('title', 'description')
    list_filter = ('delegation', 'status')
    ordering = ('due_date',)
    list_select_related = ('delegation', 'responsible')
    autocomplete_fields = ('responsible',)


@admin.register(CommitmentFollowUp)
class SeguimientoCompromisoAdmin(ScopedModelAdmin, admin.ModelAdmin):
    scope_by = 'commitment__delegation'
    list_display = ('commitment', 'date', 'responsible', 'new_status')
    search_fields = ('commitment__title',)
    list_filter = ('new_status',)
    ordering = ('-date',)
    list_select_related = ('commitment', 'responsible')
