import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Cargo, Periodo, TipoActividad

from .forms import MetaForm
from .models import Indicador
from .models import Meta as MetaModel
from .services import (
    calcular_cumplimiento_pct,
    calcular_cumplimiento_ponderado,
    calcular_meta_esperada_al_dia,
    calcular_semaforo,
)


class MetaFormTests(TestCase):
    def setUp(self):
        self.cargo = Cargo.objects.create(nombre='Encargado Social')
        self.periodo = Periodo.objects.create(
            nombre='Período 2026-1', fecha_inicio=datetime.date(2026, 1, 1),
            fecha_termino=datetime.date(2026, 6, 30),
        )
        self.tipo1 = TipoActividad.objects.create(codigo='ATC-01', nombre='Atención', categoria='atencion')
        self.tipo2 = TipoActividad.objects.create(codigo='TRA-02', nombre='Trámites', categoria='tramitacion')

    def test_suma_ponderadores_no_puede_superar_100(self):
        MetaModel.objects.create(cargo=self.cargo, periodo=self.periodo, tipo_actividad=self.tipo1, meta=10, ponderador=Decimal('70'))
        form = MetaForm(data={
            'cargo': self.cargo.pk, 'periodo': self.periodo.pk, 'tipo_actividad': self.tipo2.pk,
            'meta': 10, 'ponderador': '40',
        })
        self.assertFalse(form.is_valid())

    def test_ponderador_valido_dentro_de_100(self):
        MetaModel.objects.create(cargo=self.cargo, periodo=self.periodo, tipo_actividad=self.tipo1, meta=10, ponderador=Decimal('60'))
        form = MetaForm(data={
            'cargo': self.cargo.pk, 'periodo': self.periodo.pk, 'tipo_actividad': self.tipo2.pk,
            'meta': 10, 'ponderador': '40',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_meta_no_se_repite_para_mismo_cargo_periodo_y_tipo(self):
        MetaModel.objects.create(cargo=self.cargo, periodo=self.periodo, tipo_actividad=self.tipo1, meta=10, ponderador=Decimal('50'))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MetaModel.objects.create(
                    cargo=self.cargo, periodo=self.periodo, tipo_actividad=self.tipo1, meta=20, ponderador=Decimal('30'),
                )


class IndicadorValidationTests(TestCase):
    def setUp(self):
        self.cargo = Cargo.objects.create(nombre='Encargado Social')
        self.periodo = Periodo.objects.create(
            nombre='Período 2026-1', fecha_inicio=datetime.date(2026, 1, 1),
            fecha_termino=datetime.date(2026, 6, 30),
        )

    def test_no_permite_indicador_sin_delegacion_funcionario_ni_cargo(self):
        indicador = Indicador(
            periodo=self.periodo, fecha=datetime.date(2026, 3, 1),
            avance=1, meta=10, cumplimiento_pct=Decimal('10'), semaforo='rojo',
        )
        with self.assertRaises(ValidationError):
            indicador.clean()

    def test_no_permite_indicador_duplicado(self):
        Indicador.objects.create(
            cargo=self.cargo, periodo=self.periodo, fecha=datetime.date(2026, 3, 1),
            avance=1, meta=10, cumplimiento_pct=Decimal('10'), semaforo='rojo',
        )
        duplicado = Indicador(
            cargo=self.cargo, periodo=self.periodo, fecha=datetime.date(2026, 3, 1),
            avance=2, meta=10, cumplimiento_pct=Decimal('20'), semaforo='rojo',
        )
        with self.assertRaises(ValidationError):
            duplicado.clean()


class ServiciosCalculoTests(TestCase):
    def test_cumplimiento_pct(self):
        self.assertEqual(calcular_cumplimiento_pct(5, 10), Decimal('50'))

    def test_semaforo_verde_ambar_rojo(self):
        self.assertEqual(calcular_semaforo(Decimal('80'), Decimal('70')), 'verde')
        self.assertEqual(calcular_semaforo(Decimal('50'), Decimal('70')), 'ambar')
        self.assertEqual(calcular_semaforo(Decimal('30'), Decimal('70')), 'rojo')

    def test_cumplimiento_ponderado_respeta_tope_maximo(self):
        resultado = calcular_cumplimiento_ponderado(
            ponderador=Decimal('50'), cumplimiento_pct=Decimal('300'), tope_maximo=Decimal('150'),
        )
        self.assertEqual(resultado, Decimal('75'))

    def test_meta_esperada_al_dia(self):
        resultado = calcular_meta_esperada_al_dia(dias_transcurridos=30, dias_totales=120)
        self.assertEqual(resultado, Decimal('25'))
