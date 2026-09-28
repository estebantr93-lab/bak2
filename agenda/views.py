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
    columns = [
        Column('Título', 'title'),
        Column('Delegación', 'delegation.name'),
        Column('Responsable', 'responsible.name'),
        Column('Vence', 'due_date'),
        Column('Estado', 'get_status_display', kind='badge', badge=lambda c: f'estado-{c.status}'),
    ]


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
