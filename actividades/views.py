from core.crud import (
    Column,
    CrudConfig,
    CrudCreateView,
    CrudDeleteView,
    CrudExportView,
    CrudListView,
    CrudUpdateView,
)

from .forms import ActividadWebForm, SocialCaseForm
from .models import Activity, SocialCase


class ActivityCrud(CrudConfig):
    model = Activity
    form_class = ActividadWebForm
    select_related = ('employee', 'delegation', 'activity_type', 'period')
    title = 'Actividades'
    singular = 'actividad'
    url_prefix = 'actividad'
    columns = [
        Column('Número', 'number'),
        Column('Fecha', 'date'),
        Column('Funcionario', 'employee.name'),
        Column('Delegación', 'delegation.name'),
        Column('Tipo', 'activity_type.name'),
        Column('Período', 'period.name'),
        Column('Estado', 'get_validation_status_display', kind='badge',
               badge=lambda a: f'estado-{a.validation_status}'),
    ]
    row_links = [('Evidencias', 'evidencia_list', 'activity', 'evidencias.view_evidence')]


class SocialCaseCrud(CrudConfig):
    model = SocialCase
    form_class = SocialCaseForm
    scope_field = 'activity__delegation'
    select_related = ('activity', 'activity__delegation', 'activity__employee')
    title = 'Atenciones sociales'
    singular = 'atención social'
    url_prefix = 'atencion'
    filters = {'activity': 'activity_id'}
    columns = [
        Column('Actividad', 'activity.number'),
        Column('Delegación', 'activity.delegation.name'),
        Column('Funcionario', 'activity.employee.name'),
        Column('Gestión N°', 'step_number'),
        Column('Descripción', 'description'),
    ]


class ActividadListView(ActivityCrud, CrudListView):
    pass


class ActividadCreateView(ActivityCrud, CrudCreateView):
    pass


class ActividadUpdateView(ActivityCrud, CrudUpdateView):
    pass


class ActividadDeleteView(ActivityCrud, CrudDeleteView):
    pass


class ActividadExportView(ActivityCrud, CrudExportView):
    pass


class AtencionListView(SocialCaseCrud, CrudListView):
    pass


class AtencionCreateView(SocialCaseCrud, CrudCreateView):
    pass


class AtencionUpdateView(SocialCaseCrud, CrudUpdateView):
    pass


class AtencionDeleteView(SocialCaseCrud, CrudDeleteView):
    pass


class AtencionExportView(SocialCaseCrud, CrudExportView):
    pass
