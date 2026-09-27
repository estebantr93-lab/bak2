import datetime
from io import StringIO

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.db import connection
from django.forms import modelform_factory
from django.test import RequestFactory, TestCase

from core.testing import sembrar_datos_demo

from .admin_utils import ScopedModelAdmin
from .models import Position, Delegation, Period, ActivityType


PeriodoForm = modelform_factory(Period, fields='__all__')


class PeriodoFormTests(TestCase):
    def test_fecha_inicio_debe_ser_anterior_a_termino(self):
        form = PeriodoForm(data={
            'name': 'Período inválido',
            'start_date': datetime.date(2026, 9, 30),
            'end_date': datetime.date(2026, 6, 1),
            'is_closed': False,
            'min_threshold': '80.00',
            'max_cap': '150.00',
        })
        self.assertFalse(form.is_valid())

    def test_no_permite_solapamiento_entre_periodos(self):
        Period.objects.create(
            name='Período 1', start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 6, 30),
        )
        form = PeriodoForm(data={
            'name': 'Período 2',
            'start_date': datetime.date(2026, 6, 1),
            'end_date': datetime.date(2026, 12, 31),
            'is_closed': False,
            'min_threshold': '80.00',
            'max_cap': '150.00',
        })
        self.assertFalse(form.is_valid())

    def test_error_de_solapamiento_aparece_una_sola_vez(self):
        Period.objects.create(
            name='Período 1', start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 6, 30),
        )
        form = PeriodoForm(data={
            'name': 'Período 2', 'start_date': datetime.date(2026, 6, 1),
            'end_date': datetime.date(2026, 12, 31), 'is_closed': False,
            'min_threshold': '80.00', 'max_cap': '150.00',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors(), ['El período se solapa con otro período ya existente.'])

    def test_periodo_valido_se_guarda(self):
        form = PeriodoForm(data={
            'name': 'Período válido',
            'start_date': datetime.date(2026, 1, 1),
            'end_date': datetime.date(2026, 6, 30),
            'is_closed': False,
            'min_threshold': '80.00',
            'max_cap': '150.00',
        })
        self.assertTrue(form.is_valid(), form.errors)


class ScopingTests(TestCase):

    def setUp(self):
        from actividades.models import Activity
        from funcionarios.models import Employee

        self.centro = Delegation.objects.create(name='Centro', address='Calle 1')
        self.norte = Delegation.objects.create(name='Norte', address='Calle 2')
        cargo = Position.objects.create(name='Encargado')
        tipo = ActivityType.objects.create(code='ATC-01', name='Atención', category='service')

        user_centro = User.objects.create_user(username='func_centro', password='x', is_staff=True)
        user_norte = User.objects.create_user(username='func_norte', password='x', is_staff=True)
        self.superuser = User.objects.create_superuser(username='admin', password='x', email='a@a.com')

        self.funcionario_centro = Employee.objects.create(
            user=user_centro, delegation=self.centro, position=cargo, name='Func Centro',
        )
        funcionario_norte = Employee.objects.create(
            user=user_norte, delegation=self.norte, position=cargo, name='Func Norte',
        )

        self.actividad_centro = Activity.objects.create(
            number='ACT-C1', employee=self.funcionario_centro, delegation=self.centro, activity_type=tipo,
            date=datetime.date(2026, 6, 1), description='Centro', evidence_code='EV-C1',
        )
        self.actividad_norte = Activity.objects.create(
            number='ACT-N1', employee=funcionario_norte, delegation=self.norte, activity_type=tipo,
            date=datetime.date(2026, 6, 1), description='Norte', evidence_code='EV-N1',
        )
        self.factory = RequestFactory()
        self.user_centro = user_centro

    def test_funcionario_solo_ve_registros_de_su_delegacion(self):
        from actividades.admin import ActividadAdmin
        from actividades.models import Activity

        request = self.factory.get('/admin/actividades/activity/')
        request.user = self.user_centro
        admin_instance = ActividadAdmin(Activity, None)

        queryset = admin_instance.get_queryset(request)

        self.assertIn(self.actividad_centro, queryset)
        self.assertNotIn(self.actividad_norte, queryset)

    def test_superusuario_ve_todos_los_registros(self):
        from actividades.admin import ActividadAdmin
        from actividades.models import Activity

        request = self.factory.get('/admin/actividades/activity/')
        request.user = self.superuser
        admin_instance = ActividadAdmin(Activity, None)

        queryset = admin_instance.get_queryset(request)

        self.assertIn(self.actividad_centro, queryset)
        self.assertIn(self.actividad_norte, queryset)


class AdminConfigurationTests(TestCase):
    def test_delegacion_admin_tiene_configuracion_de_listado(self):
        from core.admin import DelegacionAdmin

        self.assertTrue(DelegacionAdmin.list_display)
        self.assertTrue(DelegacionAdmin.search_fields)
        self.assertTrue(DelegacionAdmin.list_filter)
        self.assertTrue(DelegacionAdmin.ordering)

    def test_actividad_admin_optimiza_fk_con_list_select_related(self):
        from actividades.admin import ActividadAdmin

        self.assertTrue(ActividadAdmin.list_select_related)
        for campo in ActividadAdmin.list_select_related:
            self.assertIn(campo, ['employee', 'delegation', 'activity_type', 'period'])

    def test_actividad_admin_tiene_inline_de_evidencia(self):
        from actividades.admin import ActividadAdmin, EvidenciaInline

        self.assertIn(EvidenciaInline, ActividadAdmin.inlines)

    def test_evidencia_admin_tiene_accion_aprobar_evidencias(self):
        from evidencias.admin import EvidenciaAdmin

        self.assertIn('aprobar_evidencias', EvidenciaAdmin.actions)

    def test_modelos_sensibles_usan_scoped_model_admin(self):
        from actividades.admin import ActividadAdmin, AtencionSocialAdmin
        from agenda.admin import CompromisoAdmin, SeguimientoCompromisoAdmin
        from evidencias.admin import EvidenciaAdmin, ValidacionAdmin
        from funcionarios.admin import FuncionarioAdmin
        from medicion.admin import IndicadorAdmin

        admins_sensibles = [
            ActividadAdmin, AtencionSocialAdmin, EvidenciaAdmin, ValidacionAdmin,
            CompromisoAdmin, SeguimientoCompromisoAdmin, FuncionarioAdmin, IndicadorAdmin,
        ]
        for admin_class in admins_sensibles:
            self.assertTrue(issubclass(admin_class, ScopedModelAdmin))


class BaseDatosEstructuraTests(TestCase):
    def test_no_hay_migraciones_pendientes(self):
        salida = StringIO()
        try:
            call_command('makemigrations', '--check', '--dry-run', stdout=salida, stderr=salida)
        except SystemExit:
            self.fail('Hay cambios en los modelos sin migrar: ' + salida.getvalue())

    def test_tablas_del_dominio_existen_en_la_bd(self):
        tablas = connection.introspection.table_names()
        esperadas = [
            'delegation', 'position', 'activity_type', 'period', 'parameter',
            'employee', 'password_reset_code',
            'activity', 'social_case',
            'evidence', 'validation',
            'commitment', 'commitment_follow_up',
            'goal', 'weighting', 'indicator',
            'dashboard_panel',
            'comment', 'alert', 'audit_log',
        ]
        for tabla in esperadas:
            self.assertIn(tabla, tablas)

    def test_permiso_aprobar_evidencia_existe(self):
        self.assertTrue(Permission.objects.filter(codename='can_approve_evidence').exists())


class SeedDataTests(TestCase):
    def test_seed_data_crea_las_cuentas_de_prueba(self):
        sembrar_datos_demo()
        for username in ['admin_sgr', 'funcionario_centro', 'funcionario_norte', 'verificador_leia']:
            self.assertTrue(User.objects.filter(username=username).exists())

    def test_seed_data_crea_datos_en_dos_delegaciones(self):
        from actividades.models import Activity

        sembrar_datos_demo()
        self.assertTrue(Activity.objects.filter(delegation__name='Delegación Centro').exists())
        self.assertTrue(Activity.objects.filter(delegation__name='Delegación Norte').exists())

    def test_seed_data_es_idempotente(self):
        from actividades.models import Activity

        sembrar_datos_demo()
        total_1 = Activity.objects.count()
        sembrar_datos_demo()
        total_2 = Activity.objects.count()
        self.assertEqual(total_1, total_2)


class SecretosTests(TestCase):
    def test_sin_demo_password_se_generan_claves_aleatorias_y_fuertes(self):
        import os
        from unittest import mock

        salida = StringIO()
        entorno = {k: v for k, v in os.environ.items() if not k.startswith('DEMO_PASSWORD')}
        with mock.patch.dict(os.environ, entorno, clear=True):
            call_command('seed_data', stdout=salida)
        texto = salida.getvalue()
        self.assertIn('se generaron contraseñas aleatorias', texto)
        user = User.objects.get(username='admin_centro')
        clave = texto.split('admin_centro: ')[1].split()[0]
        self.assertTrue(user.check_password(clave))
        self.assertGreaterEqual(len(clave), 10)

    def test_no_hay_contrasenas_de_demo_en_el_codigo(self):
        from funcionarios import data

        self.assertFalse(hasattr(data, 'CREDENCIALES_DEMO'))
