from core.crud import (
    Column,
    CrudConfig,
    CrudCreateView,
    CrudDeleteView,
    CrudExportView,
    CrudListView,
    CrudUpdateView,
    FiltroOpciones,
    FiltroRangoFechas,
    FiltroReciente,
    delegaciones_visibles,
    funcionarios_visibles,
    periodos,
    tipos_de_actividad,
)

from .forms import ActividadWebForm, SocialCaseForm
from .models import Activity, SocialCase, sin_evidencia


class ActivityCrud(CrudConfig):
    model = Activity
    form_class = ActividadWebForm
    select_related = ('employee', 'delegation', 'activity_type', 'period')
    title = 'Actividades'
    singular = 'actividad'
    url_prefix = 'actividad'
    columns = [
        Column('Número', 'number', sort='number'),
        Column('Fecha', 'date', sort='date'),
        Column('Funcionario', 'employee.name', kind='person', sort='employee__name'),
        Column('Delegación', 'delegation.name', sort='delegation__name'),
        Column('Tipo', 'activity_type.name', sort='activity_type__name'),
        Column('Período', 'period.name', sort='period__start_date'),
        Column('Cód. evidencia', 'evidence_code'),
        Column('Estado', 'get_validation_status_display', kind='badge',
               badge=lambda a: f'estado-{a.validation_status}', sort='validation_status'),
    ]
    search_fields = ('number', 'employee__name', 'evidence_code', 'contact', 'description')
    tabs = [
        ('todas', 'Todas', {}),
        ('pendientes', 'Pendientes', {'status': 'pending'}),
        ('aprobadas', 'Aprobadas', {'status': 'approved'}),
        ('rechazadas', 'Rechazadas', {'status': 'rejected'}),
        ('sin_evidencia', 'Sin evidencia', {'sin_evidencia': '1'}),
    ]
    kpis = [('todas', 'neutro'), ('pendientes', 'alerta'), ('aprobadas', 'bueno'), ('rechazadas', 'critico')]
    row_links = [('Evidencias', 'evidencia_list', 'activity', 'evidencias.view_evidence')]
    # Enlazados desde el dashboard: ?period=, ?status=, ?mias=1 y ?sin_evidencia=1.
    panel = [
        FiltroOpciones('period', 'Período', 'period_id', periodos),
        FiltroOpciones('delegacion', 'Delegación', 'delegation_id', delegaciones_visibles),
        FiltroOpciones('tipo', 'Tipo de actividad', 'activity_type_id', tipos_de_actividad),
        FiltroOpciones('funcionario', 'Funcionario', 'employee_id', funcionarios_visibles),
        FiltroReciente('modificada', 'Última modificación', 'updated_at'),
        FiltroRangoFechas('fecha', 'Fecha', 'date'),
    ]
    choice_filters = {'status': ('validation_status', {clave for clave, _ in Activity.STATUS_CHOICES})}
    flag_filters = {'sin_evidencia': ('sin evidencia', '_filtrar_sin_evidencia')}

    def _filtrar_sin_evidencia(self, qs):
        return sin_evidencia(qs)


class SocialCaseCrud(CrudConfig):
    model = SocialCase
    form_class = SocialCaseForm
    scope_field = 'activity__delegation'
    select_related = ('activity', 'activity__delegation', 'activity__employee')
    title = 'Atenciones sociales'
    singular = 'atención social'
    url_prefix = 'atencion'
    filters = {'activity': 'activity_id'}
    choice_filters = {'step': ('step_number', {'1', '2', '3'})}
    panel = [
        FiltroOpciones('period', 'Período', 'activity__period_id', periodos),
        FiltroOpciones('delegacion', 'Delegación', 'activity__delegation_id', delegaciones_visibles),
        FiltroOpciones('funcionario', 'Funcionario', 'activity__employee_id', funcionarios_visibles),
        FiltroReciente('modificada', 'Última modificación', 'updated_at'),
        FiltroRangoFechas('fecha', 'Fecha de la gestión', 'date'),
    ]
    columns = [
        Column('Actividad', 'activity.number', sort='activity__number'),
        Column('Delegación', 'activity.delegation.name', sort='activity__delegation__name'),
        Column('Funcionario', 'activity.employee.name', kind='person', sort='activity__employee__name'),
        Column('Gestión N°', 'step_number', sort='step_number'),
        Column('Fecha', 'date', sort='date'),
        Column('Descripción', 'description'),
        Column('Resultado', 'result'),
    ]
    search_fields = ('activity__number', 'activity__employee__name', 'description', 'result')
    tabs = [
        ('todas', 'Todas', {}),
        ('gestion_1', '1.ª gestión', {'step': '1'}),
        ('gestion_2', '2.ª gestión', {'step': '2'}),
        ('gestion_3', '3.ª gestión', {'step': '3'}),
    ]
    kpis = [('todas', 'neutro'), ('gestion_1', 'info'), ('gestion_2', 'alerta'), ('gestion_3', 'bueno')]


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
