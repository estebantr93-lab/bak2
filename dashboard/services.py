import datetime
from collections import Counter
from decimal import Decimal

from django.db.models import Count, Min, Q
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
from actividades.models import Activity
from agenda.models import Commitment
from core.models import Delegation, Period
from evidencias.models import Evidence
from funcionarios.models import Employee
from medicion.models import Goal
from medicion.services import (
    calcular_cumplimiento_ponderado,
    calcular_meta_esperada_al_dia,
    calcular_semaforo,
)

# Orden en que se muestran los grupos de rol dentro de cada delegación.
ORDEN_ROLES = [ROL_ADMIN_DELEGACION, ROL_FUNCIONARIO, ROL_VERIFICADOR, ROL_SUPERADMIN, None]
# Compromisos "por vencer": los que vencen desde hoy hasta dentro de esta cantidad de días.
DIAS_POR_VENCER = 7


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
    """Conteos por funcionario. Actividades y evidencias son del período; los compromisos son
    "a hoy" (no dependen del período elegido)."""
    filtro_periodo = Q(activities__period=periodo, activities__deleted_at__isnull=True)
    filtro_evidencias = filtro_periodo & Q(
        activities__evidence_items__isnull=False, activities__evidence_items__deleted_at__isnull=True,
    )
    compromiso_abierto = ~Q(commitments__status='done') & Q(commitments__deleted_at__isnull=True)
    por_vencer = Q(commitments__due_date__gte=hoy, commitments__due_date__lte=hoy + datetime.timedelta(days=DIAS_POR_VENCER))

    def actividades(estado):
        return Count('activities', filter=filtro_periodo & Q(activities__validation_status=estado), distinct=True)

    def evidencias(estado):
        return Count(
            'activities__evidence_items',
            filter=filtro_evidencias & Q(activities__evidence_items__status=estado), distinct=True,
        )

    return funcionarios.annotate(
        act_total=Count('activities', filter=filtro_periodo, distinct=True),
        act_aprobadas=actividades('approved'),
        act_pendientes=actividades('pending'),
        act_rechazadas=actividades('rejected'),
        evi_pendientes=evidencias('pending'),
        evi_aprobadas=evidencias('approved'),
        evi_rechazadas=evidencias('rejected'),
        comp_abiertos=Count('commitments', filter=compromiso_abierto, distinct=True),
        comp_vencidos=Count('commitments', filter=compromiso_abierto & Q(commitments__due_date__lt=hoy), distinct=True),
        comp_por_vencer=Count('commitments', filter=compromiso_abierto & por_vencer, distinct=True),
    )


def _compromisos(qs, hoy):
    """Compromisos abiertos, vencidos y por vencer de un QuerySet (a hoy, sin importar el período)."""
    abiertos = qs.exclude(status='done')
    return {
        'comp_abiertos': abiertos.count(),
        'comp_vencidos': abiertos.filter(due_date__lt=hoy).count(),
        'comp_por_vencer': abiertos.filter(
            due_date__gte=hoy, due_date__lte=hoy + datetime.timedelta(days=DIAS_POR_VENCER)).count(),
    }


def _metas_por_cargo(periodo):
    """{position_id: [Goal, ...]} del período (meta y ponderador por tipo de actividad)."""
    if periodo is None:
        return {}
    metas = {}
    for meta in Goal.objects.filter(period=periodo).select_related('activity_type').order_by('-weight'):
        metas.setdefault(meta.position_id, []).append(meta)
    return metas


def _aprobadas_por_tipo(actividades):
    """{employee_id: {activity_type_id: aprobadas}} de las actividades dadas."""
    conteo = {}
    filas = (actividades.filter(validation_status='approved')
             .values('employee_id', 'activity_type_id').annotate(n=Count('pk')))
    for fila in filas:
        conteo.setdefault(fila['employee_id'], {})[fila['activity_type_id']] = fila['n']
    return conteo


def _sin_evidencia(actividades):
    """{employee_id: actividades sin ninguna evidencia activa}."""
    filas = (actividades.annotate(n_evi=Count('evidence_items', filter=Q(evidence_items__deleted_at__isnull=True)))
             .filter(n_evi=0).values('employee_id').annotate(n=Count('pk')))
    return {fila['employee_id']: fila['n'] for fila in filas}


def _fila(funcionario, metas, aprobadas_por_tipo, sin_evidencia, esperado_pct, tope):
    metas_cargo = metas.get(funcionario.position_id, [])
    cumplimiento, detalle = calcular_cumplimiento_ponderado(aprobadas_por_tipo.get(funcionario.pk, {}), metas_cargo, tope)
    return {
        'employee': funcionario,
        'rol': get_rol(funcionario.user),
        'act_total': funcionario.act_total,
        'act_aprobadas': funcionario.act_aprobadas,
        'act_pendientes': funcionario.act_pendientes,
        'act_rechazadas': funcionario.act_rechazadas,
        'act_sin_evidencia': sin_evidencia.get(funcionario.pk, 0),
        'evi_pendientes': funcionario.evi_pendientes,
        'evi_aprobadas': funcionario.evi_aprobadas,
        'evi_rechazadas': funcionario.evi_rechazadas,
        'comp_abiertos': funcionario.comp_abiertos,
        'comp_vencidos': funcionario.comp_vencidos,
        'comp_por_vencer': funcionario.comp_por_vencer,
        'target': sum(meta.target for meta in metas_cargo),
        'aprobadas_con_meta': sum(d['aprobadas'] for d in detalle),
        'con_meta': bool(metas_cargo),
        'detalle_metas': detalle,
        'compliance_pct': cumplimiento.quantize(Decimal('0.1')),
        'traffic_light': calcular_semaforo(cumplimiento, esperado_pct) if metas_cargo else None,
    }


CAMPOS_SUMABLES = [
    'act_total', 'act_aprobadas', 'act_pendientes', 'act_rechazadas', 'act_sin_evidencia',
    'evi_pendientes', 'evi_aprobadas', 'evi_rechazadas',
    'comp_abiertos', 'comp_vencidos', 'comp_por_vencer', 'target', 'aprobadas_con_meta',
]


def _totales(filas):
    """Sumas de un grupo de filas. El cumplimiento del grupo es el promedio del cumplimiento
    ponderado de quienes tienen meta (sumar aprobadas contra metas de cargos distintos no tiene sentido)."""
    totales = {campo: sum(fila[campo] for fila in filas) for campo in CAMPOS_SUMABLES}
    totales['employees'] = len(filas)
    con_meta = [fila['compliance_pct'] for fila in filas if fila['con_meta']]
    totales['con_meta'] = len(con_meta)
    promedio = sum(con_meta) / len(con_meta) if con_meta else Decimal('0')
    totales['compliance_pct'] = Decimal(promedio).quantize(Decimal('0.1'))
    totales['evi_total'] = totales['evi_pendientes'] + totales['evi_aprobadas'] + totales['evi_rechazadas']
    revisadas = totales['evi_aprobadas'] + totales['evi_rechazadas']
    totales['evi_revisadas'] = revisadas
    totales['revision_pct'] = round(revisadas * 100 / totales['evi_total']) if totales['evi_total'] else 0
    return totales


def construir_dashboard(user, periodo, hoy=None):
    """Resumen por delegación → rol → funcionario, acotado a lo que el usuario puede ver."""
    hoy = hoy or timezone.localdate()
    esperado_pct = _porcentaje_esperado(periodo, hoy)
    tope = periodo.max_cap if periodo else None
    metas = _metas_por_cargo(periodo)
    visibles = funcionarios_visibles(user)
    actividades = Activity.objects.filter(employee__in=visibles, period=periodo) if periodo else Activity.objects.none()
    aprobadas_por_tipo = _aprobadas_por_tipo(actividades)
    sin_evidencia = _sin_evidencia(actividades)
    funcionarios = _anotar_resumen(visibles, periodo, hoy)

    filas_por_delegacion = {}
    for funcionario in funcionarios.order_by('delegation__name', 'name'):
        filas_por_delegacion.setdefault(funcionario.delegation_id, []).append(
            _fila(funcionario, metas, aprobadas_por_tipo, sin_evidencia, esperado_pct, tope)
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
        totales_seccion = _totales(filas)
        # Los compromisos de la delegación incluyen los que no tienen responsable asignado.
        totales_seccion.update(_compromisos(Commitment.objects.filter(delegation=delegacion), hoy))
        secciones.append({'delegation': delegacion, 'grupos': grupos, 'totales': totales_seccion})

    todas = [fila for filas in filas_por_delegacion.values() for fila in filas]
    totales = _totales(todas)
    if get_rol(user) != ROL_FUNCIONARIO:
        # El funcionario ve los suyos (como responsable); el resto, todos los de sus delegaciones.
        for campo in ('comp_abiertos', 'comp_vencidos', 'comp_por_vencer'):
            totales[campo] = sum(s['totales'][campo] for s in secciones)
    evidencias = Evidence.objects.filter(activity__in=actividades)
    return {
        'secciones': secciones,
        'totales': totales,
        'propia': todas[0] if get_rol(user) == ROL_FUNCIONARIO and todas else None,
        'hay_metas': bool(metas),
        'tope_pct': tope,
        'dias_por_vencer': DIAS_POR_VENCER,
        'esperado_pct': esperado_pct.quantize(Decimal('0.1')),
        'estado_actividades': _segmentos(totales, 'act_total', ESTADOS_ACTIVIDAD),
        'estado_evidencias': _segmentos(totales, 'evi_total', ESTADOS_EVIDENCIA),
        'dias_pendiente_mas_antigua': _dias_pendiente_mas_antigua(evidencias, hoy),
        'por_mes': _por_mes(actividades, 'date', periodo, hoy),
        'evidencias_por_mes': _por_mes(evidencias, 'registered_at', periodo, hoy),
        'destacados': _destacados(todas),
    }


MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
# Colores de estado: escala fija y reservada (siempre acompañada de etiqueta), validada con el
# validador de paleta del proyecto: CVD ΔE 12.3, visión normal ΔE 25.3.
ESTADOS_ACTIVIDAD = [
    ('approved', 'Aprobadas', 'act_aprobadas', 'good'),
    ('pending', 'Pendientes', 'act_pendientes', 'warning'),
    ('rejected', 'Rechazadas', 'act_rechazadas', 'critical'),
]
ESTADOS_EVIDENCIA = [
    ('approved', 'Aprobadas', 'evi_aprobadas', 'good'),
    ('pending', 'Por revisar', 'evi_pendientes', 'warning'),
    ('rejected', 'Rechazadas', 'evi_rechazadas', 'critical'),
]


def _segmentos(totales, campo_total, estados):
    """Segmentos de la dona: el círculo mide 100 unidades, así cada % es directamente un largo."""
    total = totales[campo_total]
    visibles = sum(1 for _, _, campo, _ in estados if totales[campo])
    brecha = 1.2 if visibles > 1 else 0  # separación visual entre segmentos
    segmentos, acumulado = [], 0.0
    for clave, etiqueta, campo, tono in estados:
        n = totales[campo]
        pct = (n * 100 / total) if total else 0
        largo = max(pct - brecha, 0) if n else 0
        segmentos.append({
            'clave': clave, 'etiqueta': etiqueta, 'n': n, 'tono': tono,
            'pct': round(pct, 1), 'largo': round(largo, 2), 'resto': round(100 - largo, 2),
            'offset': round(25 - acumulado, 2),  # 25 = empezar arriba (12 en punto)
        })
        acumulado += pct
    return {'total': total, 'segmentos': segmentos}


def _dias_pendiente_mas_antigua(evidencias, hoy):
    """Días que lleva esperando la evidencia pendiente más antigua (None si no hay pendientes)."""
    mas_antigua = evidencias.filter(status='pending').aggregate(m=Min('registered_at'))['m']
    if mas_antigua is None:
        return None
    return max((hoy - timezone.localdate(mas_antigua)).days, 0)


def _por_mes(qs, campo_fecha, periodo, hoy):
    """Registros del período por mes (serie única), con los meses sin registros en cero."""
    if periodo is None:
        return {'meses': [], 'maximo': 0}
    # Se agrupa en Python: con fechas-hora, agrupar en MariaDB exige tener cargadas sus tablas de zonas horarias.
    conteos = Counter()
    for valor in qs.values_list(campo_fecha, flat=True):
        fecha = timezone.localdate(valor) if isinstance(valor, datetime.datetime) else valor
        conteos[(fecha.year, fecha.month)] += 1
    meses = []
    anio, mes = periodo.start_date.year, periodo.start_date.month
    while (anio, mes) <= (periodo.end_date.year, periodo.end_date.month):
        meses.append({'etiqueta': MESES[mes - 1], 'anio': anio, 'n': conteos.get((anio, mes), 0),
                      'actual': (anio, mes) == (hoy.year, hoy.month)})
        anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    maximo = max((m['n'] for m in meses), default=0)
    for m in meses:
        m['alto'] = round(m['n'] * 100 / maximo) if maximo else 0
    return {'meses': meses, 'maximo': maximo}


def _destacados(filas, cantidad=3):
    """Funcionarios con mejor cumplimiento del período (solo quienes tienen meta)."""
    con_meta = [f for f in filas if f['con_meta']]
    con_meta.sort(key=lambda f: (f['compliance_pct'], f['aprobadas_con_meta']), reverse=True)
    return con_meta[:cantidad]
