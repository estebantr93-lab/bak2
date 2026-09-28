from decimal import Decimal

# RN-001: los ponderadores de un cargo en un período deben sumar exactamente esto.
SUMA_PONDERADORES = Decimal('100')


def suma_ponderadores(metas):
    return sum((meta.weight for meta in metas), Decimal('0'))


def formato_numero(valor):
    """100.00 → «100», 72.50 → «72,5» (Decimal.normalize() daría «1E+2»)."""
    texto = f'{Decimal(valor):.2f}'.rstrip('0').rstrip('.')
    return texto.replace('.', ',')


def calcular_cumplimiento_pct(avance, meta):
    if not meta:
        return Decimal('0')
    return (Decimal(avance) / Decimal(meta)) * 100


def calcular_cumplimiento_ponderado(aprobadas_por_tipo, metas, tope=None):
    """Cumplimiento de un funcionario según las metas (Goal) de su cargo en el período.

    - aprobadas_por_tipo: {activity_type_id: actividades aprobadas de ese tipo}.
    - metas: objetos Goal del cargo (tipo de actividad, meta y ponderador).
    - tope: % máximo que aporta cada tipo (Period.max_cap); así sobrecumplir un tipo no tapa
      el incumplimiento de otro.

    Solo cuentan las actividades de tipos con meta. Devuelve (porcentaje ponderado, detalle por tipo).
    """
    detalle, suma, suma_pesos = [], Decimal('0'), Decimal('0')
    for meta in metas:
        aprobadas = aprobadas_por_tipo.get(meta.activity_type_id, 0)
        pct = calcular_cumplimiento_pct(aprobadas, meta.target)
        aporte = min(pct, Decimal(tope)) if tope else pct
        suma += aporte * meta.weight
        suma_pesos += meta.weight
        detalle.append({
            'tipo': meta.activity_type, 'aprobadas': aprobadas, 'meta': meta.target,
            'peso': meta.weight, 'pct': pct.quantize(Decimal('0.1')),
        })
    if not suma_pesos:
        return Decimal('0'), detalle
    return suma / suma_pesos, detalle


def calcular_meta_esperada_al_dia(dias_transcurridos, dias_totales):
    if not dias_totales:
        return Decimal('0')
    return (Decimal(dias_transcurridos) / Decimal(dias_totales)) * 100


def calcular_semaforo(avance_pct, esperado_pct):
    if avance_pct >= esperado_pct:
        return 'green'
    umbral_ambar = Decimal(esperado_pct) * Decimal('0.6')
    if avance_pct >= umbral_ambar:
        return 'amber'
    return 'red'
