import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Position, Period, ActivityType

from .forms import GoalForm
from .models import Indicator
from .models import Goal
from .services import (
    calcular_cumplimiento_pct,
    calcular_meta_esperada_al_dia,
    calcular_semaforo,
)


class MetaFormTests(TestCase):
    def setUp(self):
        self.position = Position.objects.create(name='Encargado Social')
        self.period = Period.objects.create(
            name='Período 2026-1', start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 6, 30),
        )
        self.tipo1 = ActivityType.objects.create(code='ATC-01', name='Atención', category='service')
        self.tipo2 = ActivityType.objects.create(code='TRA-02', name='Trámites', category='paperwork')

    def test_suma_ponderadores_no_puede_superar_100(self):
        Goal.objects.create(position=self.position, period=self.period, activity_type=self.tipo1, target=10, weight=Decimal('70'))
        form = GoalForm(data={
            'position': self.position.pk, 'period': self.period.pk, 'activity_type': self.tipo2.pk,
            'target': 10, 'weight': '40',
        })
        self.assertFalse(form.is_valid())

    def test_ponderador_cero_muestra_un_solo_error(self):
        form = GoalForm(data={
            'position': self.position.pk, 'period': self.period.pk, 'activity_type': self.tipo1.pk,
            'target': 0, 'weight': '0',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['weight'], ['El ponderador debe ser mayor a 0.'])
        self.assertEqual(form.errors['target'], ['La meta debe ser mayor a 0.'])
        self.assertEqual(form.non_field_errors(), [])

    def test_ponderador_valido_dentro_de_100(self):
        Goal.objects.create(position=self.position, period=self.period, activity_type=self.tipo1, target=10, weight=Decimal('60'))
        form = GoalForm(data={
            'position': self.position.pk, 'period': self.period.pk, 'activity_type': self.tipo2.pk,
            'target': 10, 'weight': '40',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_meta_no_se_repite_para_mismo_cargo_periodo_y_tipo(self):
        Goal.objects.create(position=self.position, period=self.period, activity_type=self.tipo1, target=10, weight=Decimal('50'))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Goal.objects.create(
                    position=self.position, period=self.period, activity_type=self.tipo1, target=20, weight=Decimal('30'),
                )


class IndicadorValidationTests(TestCase):
    def setUp(self):
        self.position = Position.objects.create(name='Encargado Social')
        self.period = Period.objects.create(
            name='Período 2026-1', start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 6, 30),
        )

    def test_no_permite_indicador_sin_delegacion_funcionario_ni_cargo(self):
        indicador = Indicator(
            period=self.period, date=datetime.date(2026, 3, 1),
            progress=1, target=10, compliance_pct=Decimal('10'), traffic_light='red',
        )
        with self.assertRaises(ValidationError):
            indicador.clean()

    def test_no_permite_indicador_duplicado(self):
        Indicator.objects.create(
            position=self.position, period=self.period, date=datetime.date(2026, 3, 1),
            progress=1, target=10, compliance_pct=Decimal('10'), traffic_light='red',
        )
        duplicado = Indicator(
            position=self.position, period=self.period, date=datetime.date(2026, 3, 1),
            progress=2, target=10, compliance_pct=Decimal('20'), traffic_light='red',
        )
        with self.assertRaises(ValidationError):
            duplicado.clean()


class ServiciosCalculoTests(TestCase):
    def test_cumplimiento_pct(self):
        self.assertEqual(calcular_cumplimiento_pct(5, 10), Decimal('50'))

    def test_semaforo_verde_ambar_rojo(self):
        self.assertEqual(calcular_semaforo(Decimal('80'), Decimal('70')), 'green')
        self.assertEqual(calcular_semaforo(Decimal('50'), Decimal('70')), 'amber')
        self.assertEqual(calcular_semaforo(Decimal('30'), Decimal('70')), 'red')

    def test_meta_esperada_al_dia(self):
        resultado = calcular_meta_esperada_al_dia(dias_transcurridos=30, dias_totales=120)
        self.assertEqual(resultado, Decimal('25'))
