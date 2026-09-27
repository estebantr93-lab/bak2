from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from core.admin_utils import (
    ROL_ADMIN_DELEGACION,
    ROL_FUNCIONARIO,
    ROL_SUPERADMIN,
    ROL_VERIFICADOR,
    ROLES_ETIQUETAS,
    es_usuario_sin_restriccion,
    get_rol,
    get_usuario_delegacion,
)
from core.models import Delegation, Period
from funcionarios.models import Employee
from medicion.models import Goal
from medicion.services import (
    calcular_cumplimiento_pct,
    calcular_meta_esperada_al_dia,
    calcular_semaforo,
)

# Orden en que se muestran los grupos de rol dentro de cada delegación.
ORDEN_ROLES = [ROL_ADMIN_DELEGACION, ROL_FUNCIONARIO, ROL_VERIFICADOR, ROL_SUPERADMIN, None]


def periodo_por_defecto():
    """Período abierto más reciente; si no hay, el más reciente."""
    return Period.objects.filter(is_closed=False).first() or Period.objects.first()


def funcionarios_visibles(user):
    """Funcionarios que el usuario puede ver en el dashboard según su rol."""
    qs = Employee.objects.select_related('user', 'delegation', 'position').prefetch_related('user__groups')
    if es_usuario_sin_restriccion(user):
        return qs
    delegacion = get_usuario_delegacion(user)
    if delegacion is None:
        return qs.none()
    if get_rol(user) == ROL_ADMIN_DELEGACION:
        return qs.filter(delegation=delegacion)
    return qs.filter(user=user)


def delegaciones_visibles(user):
    if es_usuario_sin_restriccion(user):
        return Delegation.objects.all()
    delegacion = get_usuario_delegacion(user)
    if delegacion is None:
        return Delegation.objects.none()
    return Delegation.objects.filter(pk=delegacion.pk)


def _porcentaje_esperado(periodo, hoy):
    if periodo is None:
        return Decimal('0')
    if hoy >= periodo.end_date:
        return Decimal('100')
    if hoy <= periodo.start_date:
        return Decimal('0')
    dias_totales = (periodo.end_date - periodo.start_date).days
    dias_transcurridos = (hoy - periodo.start_date).days
    return calcular_meta_esperada_al_dia(dias_transcurridos, dias_totales)


def _anotar_resumen(funcionarios, periodo, hoy):
    filtro_periodo = Q(activities__period=periodo, activities__deleted_at__isnull=True)
    filtro_evidencias = filtro_periodo & Q(
        activities__evidence_items__isnull=False, activities__evidence_items__deleted_at__isnull=True,
    )
    compromiso_abierto = ~Q(commitments__status='done') & Q(commitments__deleted_at__isnull=True)
    return funcionarios.annotate(
        act_total=Count('activities', filter=filtro_periodo, distinct=True),
        act_aprobadas=Count(
            'activities', filter=filtro_periodo & Q(activities__validation_status='approved'), distinct=True,
        ),
        act_pendientes=Count(
            'activities', filter=filtro_periodo & Q(activities__validation_status='pending'), distinct=True,
        ),
        act_rechazadas=Count(
            'activities', filter=filtro_periodo & Q(activities__validation_status='rejected'), distinct=True,
        ),
        evi_pendientes=Count(
            'activities__evidence_items',
            filter=filtro_evidencias & Q(activities__evidence_items__status='pending'), distinct=True,
        ),
        evi_aprobadas=Count(
            'activities__evidence_items',
            filter=filtro_evidencias & Q(activities__evidence_items__status='approved'), distinct=True,
        ),
        comp_abiertos=Count('commitments', filter=compromiso_abierto, distinct=True),
        comp_vencidos=Count(
            'commitments', filter=compromiso_abierto & Q(commitments__due_date__lt=hoy), distinct=True,
        ),
    )


def _metas_por_cargo(periodo):
    if periodo is None:
        return {}
    filas = Goal.objects.filter(period=periodo).values('position_id').annotate(total=Sum('target'))
    return {fila['position_id']: fila['total'] for fila in filas}


def _fila(funcionario, metas, esperado_pct):
    meta = metas.get(funcionario.position_id, 0)
    cumplimiento = calcular_cumplimiento_pct(funcionario.act_aprobadas, meta)
    return {
        'employee': funcionario,
        'rol': get_rol(funcionario.user),
        'act_total': funcionario.act_total,
        'act_aprobadas': funcionario.act_aprobadas,
        'act_pendientes': funcionario.act_pendientes,
        'act_rechazadas': funcionario.act_rechazadas,
        'evi_pendientes': funcionario.evi_pendientes,
        'evi_aprobadas': funcionario.evi_aprobadas,
        'comp_abiertos': funcionario.comp_abiertos,
        'comp_vencidos': funcionario.comp_vencidos,
        'target': meta,
        'compliance_pct': cumplimiento.quantize(Decimal('0.1')),
        'traffic_light': calcular_semaforo(cumplimiento, esperado_pct) if meta else None,
    }


CAMPOS_SUMABLES = [
    'act_total', 'act_aprobadas', 'act_pendientes', 'act_rechazadas',
    'evi_pendientes', 'evi_aprobadas', 'comp_abiertos', 'comp_vencidos', 'target',
]


def _totales(filas):
    totales = {campo: sum(fila[campo] for fila in filas) for campo in CAMPOS_SUMABLES}
    totales['employees'] = len(filas)
    totales['compliance_pct'] = calcular_cumplimiento_pct(
        totales['act_aprobadas'], totales['target'],
    ).quantize(Decimal('0.1'))
    return totales


def construir_dashboard(user, periodo, hoy=None):
    """Resumen por delegación → rol → funcionario, acotado a lo que el usuario puede ver."""
    hoy = hoy or timezone.localdate()
    esperado_pct = _porcentaje_esperado(periodo, hoy)
    metas = _metas_por_cargo(periodo)
    funcionarios = _anotar_resumen(funcionarios_visibles(user), periodo, hoy)

    filas_por_delegacion = {}
    for funcionario in funcionarios.order_by('delegation__name', 'name'):
        filas_por_delegacion.setdefault(funcionario.delegation_id, []).append(
            _fila(funcionario, metas, esperado_pct)
        )

    secciones = []
    for delegacion in delegaciones_visibles(user):
        filas = filas_por_delegacion.get(delegacion.pk, [])
        grupos = []
        for rol in ORDEN_ROLES:
            filas_rol = [fila for fila in filas if fila['rol'] == rol]
            if filas_rol:
                grupos.append({
                    'rol': rol,
                    'etiqueta': ROLES_ETIQUETAS.get(rol, 'Sin rol asignado'),
                    'filas': filas_rol,
                    'totales': _totales(filas_rol),
                })
        secciones.append({'delegation': delegacion, 'grupos': grupos, 'totales': _totales(filas)})

    todas = [fila for filas in filas_por_delegacion.values() for fila in filas]
    return {
        'secciones': secciones,
        'totales': _totales(todas),
        'esperado_pct': esperado_pct.quantize(Decimal('0.1')),
    }
