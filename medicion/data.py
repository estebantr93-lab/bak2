import datetime
from decimal import Decimal

from actividades.models import Actividad
from core.models import Cargo, Periodo, TipoActividad
from funcionarios.models import Funcionario

from .models import Indicador, Ponderacion
from .models import Meta as MetaModel
from .services import calcular_cumplimiento_pct, calcular_meta_esperada_al_dia, calcular_semaforo

FECHA_SNAPSHOT = datetime.date(2026, 9, 14)


def build_medicion():
    periodo = Periodo.objects.get(nombre='2026-S2 (actual)')
    cargo_atencion = Cargo.objects.get(nombre='Encargado de Atención Ciudadana')
    cargo_social = Cargo.objects.get(nombre='Encargado Social')
    tipo_atc = TipoActividad.objects.get(codigo='ATC-01')
    tipo_tra = TipoActividad.objects.get(codigo='TRA-02')
    tipo_ope = TipoActividad.objects.get(codigo='OPE-03')
    tipo_soc = TipoActividad.objects.get(codigo='SOC-04')

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
            MetaModel.objects.get_or_create(
                cargo=cargo, periodo=periodo, tipo_actividad=tipo,
                defaults={'meta': meta_valor, 'ponderador': ponderador},
            )
        Ponderacion.objects.get_or_create(
            cargo=cargo, periodo=periodo,
            defaults={'detalle': {tipo.codigo: str(ponderador) for tipo, _, ponderador in metas}},
        )

    dias_totales = (periodo.fecha_termino - periodo.fecha_inicio).days
    dias_transcurridos = (FECHA_SNAPSHOT - periodo.fecha_inicio).days
    esperado_pct = calcular_meta_esperada_al_dia(dias_transcurridos, dias_totales)

    for funcionario_nombre, cargo, meta_total in [
        ('Ana Pérez (Centro)', cargo_atencion, 20),
        ('Carlos Rojas (Norte)', cargo_social, 8),
    ]:
        funcionario = Funcionario.objects.get(nombre=funcionario_nombre)
        avance = Actividad.objects.filter(
            funcionario=funcionario, periodo=periodo, estado_validacion='aprobada',
        ).count()
        cumplimiento_pct = calcular_cumplimiento_pct(avance, meta_total)
        semaforo = calcular_semaforo(cumplimiento_pct, esperado_pct)
        Indicador.objects.get_or_create(
            delegacion=funcionario.delegacion, funcionario=funcionario, cargo=cargo,
            periodo=periodo, fecha=FECHA_SNAPSHOT,
            defaults={'avance': avance, 'meta': meta_total, 'cumplimiento_pct': cumplimiento_pct, 'semaforo': semaforo},
        )
