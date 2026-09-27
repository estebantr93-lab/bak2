from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from core.admin_utils import ROLES_ETIQUETAS, get_rol, get_usuario_delegacion, tiene_acceso_al_sistema
from core.models import Periodo

from .services import construir_dashboard, periodo_por_defecto

# Clave de sesión con el período elegido: es una preferencia de navegación, no un permiso.
SESION_PERIODO = 'dashboard_periodo_id'


def _periodo_elegido(request, periodos):
    """Lee el período de ?periodo= y lo recuerda en la sesión; si no viene, usa el recordado."""
    periodo_id = request.GET.get('periodo')
    if periodo_id and periodo_id.isdigit():
        periodo = periodos.filter(pk=periodo_id).first()
        if periodo is not None:
            request.session[SESION_PERIODO] = periodo.pk
            return periodo
    periodo_id = request.session.get(SESION_PERIODO)
    if periodo_id is not None:
        periodo = periodos.filter(pk=periodo_id).first()
        if periodo is not None:
            return periodo
        request.session.pop(SESION_PERIODO, None)
    return periodo_por_defecto()


@login_required
def dashboard(request):
    # Autenticado no basta: sin rol, o sin perfil de delegación (salvo roles globales), no hay acceso.
    # El login ya lo impide; esto cubre sesiones anteriores a un cambio de rol.
    if not tiene_acceso_al_sistema(request.user):
        raise PermissionDenied('La cuenta no posee un perfil habilitado.')
    rol = get_rol(request.user)
    delegacion = get_usuario_delegacion(request.user)

    periodos = Periodo.objects.all()
    periodo = _periodo_elegido(request, periodos)
    contexto = {
        'rol': rol,
        'rol_etiqueta': ROLES_ETIQUETAS[rol],
        'delegacion_usuario': delegacion,
        'periodos': periodos,
        'periodo': periodo,
        **construir_dashboard(request.user, periodo),
    }
    return render(request, 'dashboard/index.html', contexto)
