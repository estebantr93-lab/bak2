import datetime
from io import StringIO

from django.contrib.auth.models import Permission, User
from django.core.management import call_command
from django.db import connection
from django.test import RequestFactory, TestCase

from .admin_utils import ScopedModelAdmin
from .forms import PeriodoForm
from .models import Cargo, Delegacion, Periodo, TipoActividad


class PeriodoFormTests(TestCase):
    def test_fecha_inicio_debe_ser_anterior_a_termino(self):
        form = PeriodoForm(data={
            'nombre': 'Período inválido',
            'fecha_inicio': datetime.date(2026, 9, 30),
            'fecha_termino': datetime.date(2026, 6, 1),
            'cerrado': False,
            'umbral_minimo': '80.00',
            'tope_maximo': '150.00',
        })
        self.assertFalse(form.is_valid())

    def test_no_permite_solapamiento_entre_periodos(self):
        Periodo.objects.create(
            nombre='Período 1', fecha_inicio=datetime.date(2026, 1, 1),
            fecha_termino=datetime.date(2026, 6, 30),
        )
        form = PeriodoForm(data={
            'nombre': 'Período 2',
            'fecha_inicio': datetime.date(2026, 6, 1),
            'fecha_termino': datetime.date(2026, 12, 31),
            'cerrado': False,
            'umbral_minimo': '80.00',
            'tope_maximo': '150.00',
        })
        self.assertFalse(form.is_valid())

    def test_periodo_valido_se_guarda(self):
        form = PeriodoForm(data={
            'nombre': 'Período válido',
            'fecha_inicio': datetime.date(2026, 1, 1),
            'fecha_termino': datetime.date(2026, 6, 30),
            'cerrado': False,
            'umbral_minimo': '80.00',
            'tope_maximo': '150.00',
        })
        self.assertTrue(form.is_valid(), form.errors)


class ScopingTests(TestCase):

    def setUp(self):
        from actividades.models import Actividad
        from funcionarios.models import Funcionario

        self.centro = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        self.norte = Delegacion.objects.create(nombre='Norte', direccion='Calle 2')
        cargo = Cargo.objects.create(nombre='Encargado')
        tipo = TipoActividad.objects.create(codigo='ATC-01', nombre='Atención', categoria='atencion')

        user_centro = User.objects.create_user(username='func_centro', password='x', is_staff=True)
        user_norte = User.objects.create_user(username='func_norte', password='x', is_staff=True)
        self.superuser = User.objects.create_superuser(username='admin', password='x', email='a@a.com')

        self.funcionario_centro = Funcionario.objects.create(
            user=user_centro, delegacion=self.centro, cargo=cargo, nombre='Func Centro',
        )
        funcionario_norte = Funcionario.objects.create(
            user=user_norte, delegacion=self.norte, cargo=cargo, nombre='Func Norte',
        )

        self.actividad_centro = Actividad.objects.create(
            numero='ACT-C1', funcionario=self.funcionario_centro, delegacion=self.centro, tipo_actividad=tipo,
            fecha=datetime.date(2026, 6, 1), descripcion='Centro', codigo_evidencia='EV-C1',
        )
        self.actividad_norte = Actividad.objects.create(
            numero='ACT-N1', funcionario=funcionario_norte, delegacion=self.norte, tipo_actividad=tipo,
            fecha=datetime.date(2026, 6, 1), descripcion='Norte', codigo_evidencia='EV-N1',
        )
        self.factory = RequestFactory()
        self.user_centro = user_centro

    def test_funcionario_solo_ve_registros_de_su_delegacion(self):
        from actividades.admin import ActividadAdmin
        from actividades.models import Actividad

        request = self.factory.get('/admin/actividades/actividad/')
        request.user = self.user_centro
        admin_instance = ActividadAdmin(Actividad, None)

        queryset = admin_instance.get_queryset(request)

        self.assertIn(self.actividad_centro, queryset)
        self.assertNotIn(self.actividad_norte, queryset)

    def test_superusuario_ve_todos_los_registros(self):
        from actividades.admin import ActividadAdmin
        from actividades.models import Actividad

        request = self.factory.get('/admin/actividades/actividad/')
        request.user = self.superuser
        admin_instance = ActividadAdmin(Actividad, None)

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
            self.assertIn(campo, ['funcionario', 'delegacion', 'tipo_actividad', 'periodo'])

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
            'core_delegacion', 'core_cargo', 'core_tipoactividad', 'core_periodo', 'core_parametro',
            'funcionarios_funcionario',
            'actividades_actividad', 'actividades_atencionsocial',
            'evidencias_evidencia', 'evidencias_validacion',
            'agenda_compromiso', 'agenda_seguimientocompromiso',
            'medicion_meta', 'medicion_ponderacion', 'medicion_indicador',
            'monitoreo_tableropanel',
            'colaboracion_comentario', 'colaboracion_alerta', 'colaboracion_trazaauditoria',
        ]
        for tabla in esperadas:
            self.assertIn(tabla, tablas)

    def test_permiso_aprobar_evidencia_existe(self):
        self.assertTrue(Permission.objects.filter(codename='can_approve_evidencia').exists())


class SeedDataTests(TestCase):
    def test_seed_data_crea_las_cuentas_de_prueba(self):
        call_command('seed_data', stdout=StringIO())
        for username in ['admin_sgr', 'funcionario_centro', 'funcionario_norte', 'verificador_leia']:
            self.assertTrue(User.objects.filter(username=username).exists())

    def test_seed_data_crea_datos_en_dos_delegaciones(self):
        from actividades.models import Actividad

        call_command('seed_data', stdout=StringIO())
        self.assertTrue(Actividad.objects.filter(delegacion__nombre='Delegación Centro').exists())
        self.assertTrue(Actividad.objects.filter(delegacion__nombre='Delegación Norte').exists())

    def test_seed_data_es_idempotente(self):
        from actividades.models import Actividad

        call_command('seed_data', stdout=StringIO())
        total_1 = Actividad.objects.count()
        call_command('seed_data', stdout=StringIO())
        total_2 = Actividad.objects.count()
        self.assertEqual(total_1, total_2)
