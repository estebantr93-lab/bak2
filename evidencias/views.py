from core.crud import (
    Column,
    CrudConfig,
    CrudCreateView,
    CrudDeleteView,
    CrudExportView,
    CrudListView,
    CrudUpdateView,
)

from .forms import EvidenciaForm
from .models import Evidence


class EvidenceCrud(CrudConfig):
    model = Evidence
    form_class = EvidenciaForm
    scope_field = 'activity__delegation'
    select_related = ('activity', 'activity__delegation', 'reviewed_by')
    title = 'Evidencias'
    singular = 'evidencia'
    url_prefix = 'evidencia'
    # ?activity=<id> desde el listado de actividades; ?period=<id> desde el dashboard.
    filters = {'activity': 'activity_id', 'period': 'activity__period_id'}
    # /evidencias/?status=pending (cola del verificador) o ?status=rejected (por corregir), desde el dashboard.
    choice_filters = {'status': ('status', {clave for clave, _ in Evidence.STATUS_CHOICES})}
    columns = [
        Column('Código', 'unique_code'),
        Column('Actividad', 'activity.number'),
        Column('Delegación', 'activity.delegation.name'),
        Column('Archivo', 'file', kind='file'),
        Column('Registrada', 'registered_at'),
        Column('Estado', 'get_status_display', kind='badge', badge=lambda e: f'estado-{e.status}'),
        Column('Revisada por', 'reviewed_by'),
    ]


class EvidenciaListView(EvidenceCrud, CrudListView):
    pass


class EvidenciaCreateView(EvidenceCrud, CrudCreateView):
    def get_initial(self):
        # Si se llega desde una actividad (?activity=<id>), se preselecciona.
        return {'activity': self.active_filters().get('activity')}


class EvidenciaUpdateView(EvidenceCrud, CrudUpdateView):
    pass


class EvidenciaDeleteView(EvidenceCrud, CrudDeleteView):
    pass


class EvidenciaExportView(EvidenceCrud, CrudExportView):
    pass
