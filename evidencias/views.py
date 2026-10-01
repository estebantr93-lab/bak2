import os

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404

from core.admin_utils import filtrar_por_delegacion, ve_eliminados
from core.crud import (
    Column,
    CrudConfig,
    CrudCreateView,
    CrudDeleteView,
    CrudExportView,
    CrudListView,
    CrudUpdateView,
    FiltroCondiciones,
    FiltroOpciones,
    FiltroRangoFechas,
    FiltroReciente,
    delegaciones_visibles,
    periodos,
    tipos_de_actividad,
)

from .archivos import TIPO_POR_EXTENSION
from .forms import EvidenciaForm
from .models import Evidence


def revisores_visibles(vista):
    """Quienes revisaron evidencias del alcance del usuario (no se listan revisores de otras delegaciones)."""
    revisadas = filtrar_por_delegacion(Evidence.objects.filter(reviewed_by__isnull=False), vista.request.user, 'activity__delegation')
    return revisadas.order_by('reviewed_by__username').values_list('reviewed_by_id', 'reviewed_by__username').distinct()


class EvidenceCrud(CrudConfig):
    model = Evidence
    form_class = EvidenciaForm
    scope_field = 'activity__delegation'
    select_related = ('activity', 'activity__delegation', 'reviewed_by')
    title = 'Evidencias'
    singular = 'evidencia'
    url_prefix = 'evidencia'
    # ?activity=<id> desde el listado de actividades; ?period=<id> desde el dashboard (panel).
    filters = {'activity': 'activity_id'}
    # /evidencias/?status=pending (cola del verificador) o ?status=rejected (por corregir), desde el dashboard.
    choice_filters = {'status': ('status', {clave for clave, _ in Evidence.STATUS_CHOICES})}
    columns = [
        Column('Código', 'unique_code', sort='unique_code'),
        Column('Actividad', 'activity.number', sort='activity__number'),
        Column('Delegación', 'activity.delegation.name', sort='activity__delegation__name'),
        Column('Archivo', 'file', kind='file'),
        Column('Registrada', 'registered_at', sort='registered_at'),
        Column('Estado', 'get_status_display', kind='badge', badge=lambda e: f'estado-{e.status}', sort='status'),
        Column('Revisada por', 'reviewed_by', kind='person', sort='reviewed_by__username'),
        Column('Modificada', 'updated_at', sort='updated_at'),
    ]
    panel = [
        FiltroReciente('modificada', 'Última modificación', 'updated_at'),
        FiltroOpciones('period', 'Período', 'activity__period_id', periodos),
        FiltroOpciones('delegacion', 'Delegación', 'activity__delegation_id', delegaciones_visibles),
        FiltroOpciones('tipo', 'Tipo de actividad', 'activity__activity_type_id', tipos_de_actividad),
        FiltroOpciones('revisor', 'Revisada por', 'reviewed_by_id', revisores_visibles, minimo=1),
        FiltroCondiciones('archivo', 'Archivo', [
            ('con', 'Con archivo', Q(file__isnull=False) & ~Q(file='')),
            ('sin', 'Sin archivo', Q(file__isnull=True) | Q(file='')),
        ]),
        FiltroRangoFechas('registrada', 'Registrada', 'registered_at', con_hora=True),
    ]
    search_fields = ('unique_code', 'activity__number', 'description')
    tabs = [
        ('todas', 'Todas', {}),
        ('pendientes', 'Por revisar', {'status': 'pending'}),
        ('aprobadas', 'Aprobadas', {'status': 'approved'}),
        ('rechazadas', 'Rechazadas', {'status': 'rejected'}),
    ]
    kpis = [('todas', 'neutro'), ('pendientes', 'alerta'), ('aprobadas', 'bueno'), ('rechazadas', 'critico')]


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


@login_required
def archivo_evidencia(request, nombre):
    """Entrega el archivo de una evidencia solo a quien puede ver esa evidencia.

    Los archivos no se publican en una carpeta abierta (/media/): conocer o compartir el enlace no
    basta. Se exige sesión, el permiso de ver evidencias y que la evidencia sea de su alcance
    (delegación); fuera de él la respuesta es 404, igual que en el CRUD. `nombre` solo se busca en la
    base de datos, nunca se usa para abrir una ruta del disco."""
    if not request.user.has_perm('evidencias.view_evidence'):
        raise PermissionDenied
    evidencias = Evidence.all_objects if ve_eliminados(request.user) else Evidence.objects
    evidencia = filtrar_por_delegacion(evidencias.filter(file=nombre), request.user, 'activity__delegation').first()
    extension = os.path.splitext(nombre)[1].lower()
    if evidencia is None or extension not in TIPO_POR_EXTENSION or not evidencia.archivo_disponible:
        raise Http404('Archivo no encontrado.')
    respuesta = FileResponse(
        evidencia.file.open('rb'), content_type=TIPO_POR_EXTENSION[extension],  # tipo según la extensión validada
        filename=f'{evidencia.unique_code}{extension}',
    )
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, no-store'  # datos personales: no quedan en cachés compartidas
    return respuesta
