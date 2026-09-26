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
from core.models import Delegacion, Periodo
from funcionarios.models import Funcionario
from medicion.models import Meta as MetaModel
from medicion.services import (
    calcular_cumplimiento_pct,
    calcular_meta_esperada_al_dia,
    calcular_semaforo,
)

# Orden en que se muestran los grupos de rol dentro de cada delegación.
ORDEN_ROLES = [ROL_ADMIN_DELEGACION, ROL_FUNCIONARIO, ROL_VERIFICADOR, ROL_SUPERADMIN, None]


def periodo_por_defecto():
    """Período abierto más reciente; si no hay, el más reciente."""
    return Periodo.objects.filter(cerrado=False).first() or Periodo.objects.first()


def funcionarios_visibles(user):
    """Funcionarios que el usuario puede ver en el dashboard según su rol."""
    qs = Funcionario.objects.select_related('user', 'delegacion', 'cargo').prefetch_related('user__groups')
    if es_usuario_sin_restriccion(user):
        return qs
    delegacion = get_usuario_delegacion(user)
    if delegacion is None:
        return qs.none()
    if get_rol(user) == ROL_ADMIN_DELEGACION:
        return qs.filter(delegacion=delegacion)
    return qs.filter(user=user)


def delegaciones_visibles(user):
    if es_usuario_sin_restriccion(user):
        return Delegacion.objects.all()
    delegacion = get_usuario_delegacion(user)
    if delegacion is None:
        return Delegacion.objects.none()
    return Delegacion.objects.filter(pk=delegacion.pk)


def _porcentaje_esperado(periodo, hoy):
    if periodo is None:
        return Decimal('0')
    if hoy >= periodo.fecha_termino:
        return Decimal('100')
    if hoy <= periodo.fecha_inicio:
        return Decimal('0')
    dias_totales = (periodo.fecha_termino - periodo.fecha_inicio).days
    dias_transcurridos = (hoy - periodo.fecha_inicio).days
    return calcular_meta_esperada_al_dia(dias_transcurridos, dias_totales)


def _anotar_resumen(funcionarios, periodo, hoy):
    filtro_periodo = Q(actividades__periodo=periodo)
    filtro_evidencias = Q(actividades__evidencias__isnull=False, actividades__periodo=periodo)
    compromiso_abierto = ~Q(compromisos__estado='realizado')
    return funcionarios.annotate(
        act_total=Count('actividades', filter=filtro_periodo, distinct=True),
        act_aprobadas=Count(
            'actividades', filter=filtro_periodo & Q(actividades__estado_validacion='aprobada'), distinct=True,
        ),
        act_pendientes=Count(
            'actividades', filter=filtro_periodo & Q(actividades__estado_validacion='pendiente'), distinct=True,
        ),
        act_rechazadas=Count(
            'actividades', filter=filtro_periodo & Q(actividades__estado_validacion='rechazada'), distinct=True,
        ),
        evi_pendientes=Count(
            'actividades__evidencias',
            filter=filtro_evidencias & Q(actividades__evidencias__estado='pendiente'), distinct=True,
        ),
        evi_aprobadas=Count(
            'actividades__evidencias',
            filter=filtro_evidencias & Q(actividades__evidencias__estado='aprobada'), distinct=True,
        ),
        comp_abiertos=Count('compromisos', filter=compromiso_abierto, distinct=True),
        comp_vencidos=Count(
            'compromisos', filter=compromiso_abierto & Q(compromisos__fecha_vencimiento__lt=hoy), distinct=True,
        ),
    )


def _metas_por_cargo(periodo):
    if periodo is None:
        return {}
    filas = MetaModel.objects.filter(periodo=periodo).values('cargo_id').annotate(total=Sum('meta'))
    return {fila['cargo_id']: fila['total'] for fila in filas}


def _fila(funcionario, metas, esperado_pct):
    meta = metas.get(funcionario.cargo_id, 0)
    cumplimiento = calcular_cumplimiento_pct(funcionario.act_aprobadas, meta)
    return {
        'funcionario': funcionario,
        'rol': get_rol(funcionario.user),
        'act_total': funcionario.act_total,
        'act_aprobadas': funcionario.act_aprobadas,
        'act_pendientes': funcionario.act_pendientes,
        'act_rechazadas': funcionario.act_rechazadas,
        'evi_pendientes': funcionario.evi_pendientes,
        'evi_aprobadas': funcionario.evi_aprobadas,
        'comp_abiertos': funcionario.comp_abiertos,
        'comp_vencidos': funcionario.comp_vencidos,
        'meta': meta,
        'cumplimiento_pct': cumplimiento.quantize(Decimal('0.1')),
        'semaforo': calcular_semaforo(cumplimiento, esperado_pct) if meta else None,
    }


CAMPOS_SUMABLES = [
    'act_total', 'act_aprobadas', 'act_pendientes', 'act_rechazadas',
    'evi_pendientes', 'evi_aprobadas', 'comp_abiertos', 'comp_vencidos', 'meta',
]


def _totales(filas):
    totales = {campo: sum(fila[campo] for fila in filas) for campo in CAMPOS_SUMABLES}
    totales['funcionarios'] = len(filas)
    totales['cumplimiento_pct'] = calcular_cumplimiento_pct(
        totales['act_aprobadas'], totales['meta'],
    ).quantize(Decimal('0.1'))
    return totales


def construir_dashboard(user, periodo, hoy=None):
    """Resumen por delegación → rol → funcionario, acotado a lo que el usuario puede ver."""
    hoy = hoy or timezone.localdate()
    esperado_pct = _porcentaje_esperado(periodo, hoy)
    metas = _metas_por_cargo(periodo)
    funcionarios = _anotar_resumen(funcionarios_visibles(user), periodo, hoy)

    filas_por_delegacion = {}
    for funcionario in funcionarios.order_by('delegacion__nombre', 'nombre'):
        filas_por_delegacion.setdefault(funcionario.delegacion_id, []).append(
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
        secciones.append({'delegacion': delegacion, 'grupos': grupos, 'totales': _totales(filas)})

    todas = [fila for filas in filas_por_delegacion.values() for fila in filas]
    return {
        'secciones': secciones,
        'totales': _totales(todas),
        'esperado_pct': esperado_pct.quantize(Decimal('0.1')),
    }
