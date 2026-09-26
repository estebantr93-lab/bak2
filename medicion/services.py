from decimal import Decimal


def calcular_avance(actividades_validas_qs):
    return actividades_validas_qs.count()


def calcular_cumplimiento_pct(avance, meta):
    if not meta:
        return Decimal('0')
    return (Decimal(avance) / Decimal(meta)) * 100


def calcular_cumplimiento_ponderado(ponderador, cumplimiento_pct, tope_maximo=Decimal('150')):
    cumplimiento_pct = min(cumplimiento_pct, tope_maximo)
    return (Decimal(ponderador) * cumplimiento_pct) / 100


def calcular_meta_esperada_al_dia(dias_transcurridos, dias_totales):
    if not dias_totales:
        return Decimal('0')
    return (Decimal(dias_transcurridos) / Decimal(dias_totales)) * 100


def calcular_semaforo(avance_pct, esperado_pct):
    if avance_pct >= esperado_pct:
        return 'verde'
    umbral_ambar = Decimal(esperado_pct) * Decimal('0.6')
    if avance_pct >= umbral_ambar:
        return 'ambar'
    return 'rojo'
