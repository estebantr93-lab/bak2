from core.crud import (
    Column,
    CrudConfig,
    CrudCreateView,
    CrudDeleteView,
    CrudExportView,
    CrudListView,
    CrudUpdateView,
)

from .forms import CommitmentForm
from .models import Commitment


class CommitmentCrud(CrudConfig):
    model = Commitment
    form_class = CommitmentForm
    select_related = ('delegation', 'responsible')
    title = 'Compromisos'
    singular = 'compromiso'
    femenino = False
    url_prefix = 'compromiso'
    context_object_name = 'commitments'
    owner_field = 'responsible'
    columns = [
        Column('Título', 'title'),
        Column('Delegación', 'delegation.name'),
        Column('Responsable', 'responsible.name'),
        Column('Vence', 'due_date'),
        Column('Estado', 'get_status_display', kind='badge', badge=lambda c: f'estado-{c.status}'),
    ]


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
