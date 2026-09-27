import datetime
from decimal import Decimal

from actividades.models import Activity
from core.models import Position, Period, ActivityType
from funcionarios.models import Employee

from .models import Indicator, Weighting
from .models import Goal
from .services import calcular_cumplimiento_pct, calcular_meta_esperada_al_dia, calcular_semaforo

FECHA_SNAPSHOT = datetime.date(2026, 9, 14)


def build_medicion():
    periodo = Period.objects.get(name='2026-S2 (actual)')
    cargo_atencion = Position.objects.get(name='Encargado de Atención Ciudadana')
    cargo_social = Position.objects.get(name='Encargado Social')
    tipo_atc = ActivityType.objects.get(code='ATC-01')
    tipo_tra = ActivityType.objects.get(code='TRA-02')
    tipo_ope = ActivityType.objects.get(code='OPE-03')
    tipo_soc = ActivityType.objects.get(code='SOC-04')

    metas_atencion = [
        (tipo_atc, 20, Decimal('50')),
        (tipo_tra, 15, Decimal('30')),
        (tipo_ope, 10, Decimal('20')),
    ]
    metas_social = [
        (tipo_soc, 8, Decimal('70')),
        (tipo_atc, 5, Decimal('30')),
    ]

    for cargo, metas in [(cargo_atencion, metas_atencion), (cargo_social, metas_social)]:
        for tipo, meta_valor, ponderador in metas:
            Goal.objects.get_or_create(
                position=cargo, period=periodo, activity_type=tipo,
                defaults={'target': meta_valor, 'weight': ponderador},
            )
        Weighting.objects.get_or_create(
            position=cargo, period=periodo,
            defaults={'detail': {tipo.code: str(ponderador) for tipo, _, ponderador in metas}},
        )

    dias_totales = (periodo.end_date - periodo.start_date).days
    dias_transcurridos = (FECHA_SNAPSHOT - periodo.start_date).days
    esperado_pct = calcular_meta_esperada_al_dia(dias_transcurridos, dias_totales)

    for funcionario_nombre, cargo, meta_total in [
        ('Ana Pérez (Centro)', cargo_atencion, 20),
        ('Carlos Rojas (Norte)', cargo_social, 8),
    ]:
        funcionario = Employee.objects.get(name=funcionario_nombre)
        avance = Activity.objects.filter(
            employee=funcionario, period=periodo, validation_status='approved',
        ).count()
        cumplimiento_pct = calcular_cumplimiento_pct(avance, meta_total)
        semaforo = calcular_semaforo(cumplimiento_pct, esperado_pct)
        Indicator.objects.get_or_create(
            delegation=funcionario.delegation, employee=funcionario, position=cargo,
            period=periodo, date=FECHA_SNAPSHOT,
            defaults={'progress': avance, 'target': meta_total, 'compliance_pct': cumplimiento_pct, 'traffic_light': semaforo},
        )
