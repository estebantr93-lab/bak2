from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from core.admin_utils import (
    ROL_FUNCIONARIO,
    ROL_VERIFICADOR,
    ROLES_ETIQUETAS,
    es_usuario_sin_restriccion,
    get_rol,
    get_usuario_delegacion,
    tiene_acceso_al_sistema,
)
from core.models import Period

from .services import construir_dashboard, periodo_por_defecto

# Clave de sesión con el período elegido: es una preferencia de navegación, no un permiso.
SESION_PERIODO = 'dashboard_periodo_id'


def _periodo_elegido(request, periodos):
    """Lee el período de ?periodo= y lo recuerda en la sesión; si no viene, usa el recordado."""
    periodo_id = request.GET.get('period')
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


def _url_si_puede(user, permiso, nombre_url, consulta=''):
    """Enlace a una lista solo si el usuario puede verla (no se ofrecen enlaces que terminan en 403)."""
    if not user.has_perm(permiso):
        return None
    return reverse(nombre_url) + (f'?{consulta}' if consulta else '')


def _indicadores(user, rol, datos, delegacion):
    """Los 4 indicadores superiores, según lo que le sirve a cada rol."""
    t = datos['totales']
    evidencias_pendientes = _url_si_puede(user, 'evidencias.view_evidence', 'evidencia_list', 'status=pending')
    if rol == ROL_FUNCIONARIO:
        return [
            {'tono': 2, 'icono': 'lista', 'etiqueta': 'Mis actividades', 'valor': t['act_total'],
             'nota': f"{t['act_aprobadas']} aprobadas",
             'url': _url_si_puede(user, 'actividades.view_activity', 'actividad_list')},
            {'tono': 3, 'icono': 'documento', 'etiqueta': 'Actividades sin evidencia', 'valor': t['act_sin_evidencia'],
             'nota': 'suba su respaldo',
             'url': _url_si_puede(user, 'actividades.view_activity', 'actividad_list')},
            {'tono': 1, 'icono': 'alerta', 'etiqueta': 'Evidencias rechazadas', 'valor': t['evi_rechazadas'],
             'nota': 'suba una corregida',
             'url': _url_si_puede(user, 'evidencias.view_evidence', 'evidencia_list', 'status=rejected')},
            {'tono': 4, 'icono': 'calendario', 'etiqueta': 'Compromisos por vencer', 'valor': t['comp_por_vencer'],
             'nota': f"próximos {datos['dias_por_vencer']} días · {t['comp_vencidos']} vencidos",
             'url': _url_si_puede(user, 'agenda.view_commitment', 'compromiso_list')},
        ]
    if rol == ROL_VERIFICADOR:
        dias = datos['dias_pendiente_mas_antigua']
        return [
            {'tono': 3, 'icono': 'documento', 'etiqueta': 'Evidencias por revisar', 'valor': t['evi_pendientes'],
             'nota': 'del período', 'url': evidencias_pendientes},
            {'tono': 4, 'icono': 'reloj', 'etiqueta': 'Espera más larga', 'valor': '—' if dias is None else f'{dias} d',
             'nota': 'sin pendientes' if dias is None else 'pendiente más antigua'},
            {'tono': 2, 'icono': 'check', 'etiqueta': 'Revisadas', 'valor': t['evi_revisadas'],
             'nota': f"de {t['evi_total']} del período"},
            {'tono': 1, 'icono': 'alerta', 'etiqueta': 'Rechazadas', 'valor': t['evi_rechazadas'],
             'nota': 'a la espera de corrección',
             'url': _url_si_puede(user, 'evidencias.view_evidence', 'evidencia_list', 'status=rejected')},
        ]
    return [
        {'tono': 1, 'icono': 'personas', 'etiqueta': 'Funcionarios', 'valor': t['employees'],
         'nota': 'en su delegación' if delegacion else 'en ambas delegaciones'},
        {'tono': 2, 'icono': 'lista', 'etiqueta': 'Actividades', 'valor': t['act_total'],
         'nota': f"{t['act_aprobadas']} aprobadas",
         'url': _url_si_puede(user, 'actividades.view_activity', 'actividad_list')},
        {'tono': 3, 'icono': 'documento', 'etiqueta': 'Evidencias por revisar', 'valor': t['evi_pendientes'],
         'nota': 'del período', 'url': evidencias_pendientes},
        {'tono': 4, 'icono': 'calendario', 'etiqueta': 'Compromisos vencidos', 'valor': t['comp_vencidos'],
         'nota': f"a hoy · de {t['comp_abiertos']} abiertos",
         'url': _url_si_puede(user, 'agenda.view_commitment', 'compromiso_list')},
    ]


@login_required
def dashboard(request):
    # Autenticado no basta: sin rol, o sin perfil de delegación (salvo roles globales), no hay acceso.
    # El login ya lo impide; esto cubre sesiones anteriores a un cambio de rol.
    if not tiene_acceso_al_sistema(request.user):
        raise PermissionDenied('La cuenta no posee un perfil habilitado.')
    rol = get_rol(request.user)
    delegacion = get_usuario_delegacion(request.user)

    periodos = Period.objects.all()
    periodo = _periodo_elegido(request, periodos)
    hora = timezone.localtime().hour
    saludo = 'Buenos días' if hora < 12 else 'Buenas tardes' if hora < 20 else 'Buenas noches'
    datos = construir_dashboard(request.user, periodo)
    # Los roles globales ven ambas delegaciones: no se muestra una delegación propia.
    delegacion_propia = None if es_usuario_sin_restriccion(request.user) else delegacion
    contexto = {
        'saludo': saludo,
        'rol': rol,
        'rol_etiqueta': ROLES_ETIQUETAS[rol],
        # Qué ve cada rol: el funcionario, su propio avance; el verificador, la cola de revisión;
        # los administradores (de delegación y general), el avance de su equipo.
        'es_funcionario': rol == ROL_FUNCIONARIO,
        'es_verificador': rol == ROL_VERIFICADOR,
        'es_gestor': rol not in (ROL_FUNCIONARIO, ROL_VERIFICADOR),
        'delegacion_usuario': delegacion_propia,
        'periodos': periodos,
        'period': periodo,
        'indicadores': _indicadores(request.user, rol, datos, delegacion_propia),
        'url_evidencias_pendientes': _url_si_puede(
            request.user, 'evidencias.view_evidence', 'evidencia_list', 'status=pending'),
        **datos,
    }
    return render(request, 'dashboard/index.html', contexto)
