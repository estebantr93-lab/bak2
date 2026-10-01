from core.crud import (
    Column,
    CrudConfig,
    CrudCreateView,
    CrudDeleteView,
    CrudExportView,
    CrudListView,
    CrudUpdateView,
)

from django.utils import timezone

from .forms import CommitmentForm
from .models import DIAS_POR_VENCER, Commitment, compromisos_por_vencer, compromisos_vencidos


class CommitmentCrud(CrudConfig):
    model = Commitment
    form_class = CommitmentForm
    select_related = ('delegation', 'responsible')
    title = 'Compromisos'
    singular = 'compromiso'
    femenino = False
    url_prefix = 'compromiso'
    # Enlazados desde el dashboard: la lista muestra lo mismo que cuenta el indicador.
    flag_filters = {
        'vencidos': ('vencidos a hoy', '_filtrar_vencidos'),
        'por_vencer': (f'vencen en los próximos {DIAS_POR_VENCER} días', '_filtrar_por_vencer'),
    }
    choice_filters = {'status': ('status', {clave for clave, _ in Commitment.STATUS_CHOICES})}
    columns = [
        Column('Título', 'title', sort='title'),
        Column('Delegación', 'delegation.name', sort='delegation__name'),
        Column('Responsable', 'responsible.name', kind='person', sort='responsible__name'),
        Column('Vence', 'due_date', sort='due_date'),
        Column('Estado', 'get_status_display', kind='badge', badge=lambda c: f'estado-{c.status}', sort='status'),
    ]
    search_fields = ('title', 'description', 'responsible__name')
    tabs = [
        ('todos', 'Todos', {}),
        ('en_proceso', 'En proceso', {'status': 'in_progress'}),
        ('vencidos', 'Vencidos', {'vencidos': '1'}),
        ('por_vencer', f'Vencen en {DIAS_POR_VENCER} días', {'por_vencer': '1'}),
        ('realizados', 'Realizados', {'status': 'done'}),
    ]
    kpis = [('todos', 'neutro'), ('en_proceso', 'info'), ('vencidos', 'critico'), ('realizados', 'bueno')]


    def _filtrar_vencidos(self, qs):
        return compromisos_vencidos(qs, timezone.localdate())

    def _filtrar_por_vencer(self, qs):
        return compromisos_por_vencer(qs, timezone.localdate())


class CompromisoListView(CommitmentCrud, CrudListView):
    pass


class CompromisoCreateView(CommitmentCrud, CrudCreateView):
    pass


class CompromisoUpdateView(CommitmentCrud, CrudUpdateView):
    pass


class CompromisoDeleteView(CommitmentCrud, CrudDeleteView):
    pass


class CompromisoExportView(CommitmentCrud, CrudExportView):
    pass
