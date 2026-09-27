import datetime

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase

from core.models import Position, Delegation, ActivityType
from funcionarios.models import Employee
from actividades.models import Activity
from core.testing import CLAVE_TEST, sembrar_datos_demo

from .admin import EvidenciaAdmin
from .models import Evidence, Validation


class AprobarEvidenciasActionTests(TestCase):
    def setUp(self):
        delegacion = Delegation.objects.create(name='Centro', address='Calle 1')
        cargo = Position.objects.create(name='Verificador')
        tipo = ActivityType.objects.create(code='ATC-01', name='Atención', category='service')
        func_user = User.objects.create_user(username='func', password='x')
        funcionario = Employee.objects.create(user=func_user, delegation=delegacion, position=cargo, name='Func')
        actividad = Activity.objects.create(
            number='ACT-1', employee=funcionario, delegation=delegacion, activity_type=tipo,
            date=datetime.date(2026, 6, 1), description='desc', evidence_code='EV-100',
        )
        self.evidence = Evidence.objects.create(unique_code='EVI-001', activity=actividad)

        ct = ContentType.objects.get_for_model(Evidence)
        self.permiso_aprobar = Permission.objects.get(content_type=ct, codename='can_approve_evidence')
        self.reviewer = User.objects.create_user(username='reviewer', password='x', is_staff=True)
        self.reviewer.user_permissions.add(self.permiso_aprobar)

        self.sin_permiso = User.objects.create_user(username='sinpermiso', password='x', is_staff=True)

        self.factory = RequestFactory()

    def _request_con_mensajes(self, usuario):
        request = self.factory.post('/admin/evidencias/evidence/')
        request.user = usuario
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_aprobar_evidencias_cambia_estado_y_crea_validacion(self):
        request = self._request_con_mensajes(self.reviewer)
        admin_instance = EvidenciaAdmin(Evidence, None)

        admin_instance.aprobar_evidencias(request, Evidence.objects.filter(pk=self.evidence.pk))

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.status, 'approved')
        self.assertEqual(self.evidence.reviewed_by, self.reviewer)
        self.assertTrue(Validation.objects.filter(evidence=self.evidence, status='approved').exists())

    def test_usuario_sin_permiso_no_puede_aprobar(self):
        request = self._request_con_mensajes(self.sin_permiso)
        admin_instance = EvidenciaAdmin(Evidence, None)

        admin_instance.aprobar_evidencias(request, Evidence.objects.filter(pk=self.evidence.pk))

        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.status, 'pending')
        self.assertFalse(Validation.objects.filter(evidence=self.evidence).exists())


class EvidenciaUnicidadTests(TestCase):
    def setUp(self):
        delegacion = Delegation.objects.create(name='Centro', address='Calle 1')
        cargo = Position.objects.create(name='Encargado')
        tipo = ActivityType.objects.create(code='ATC-01', name='Atención', category='service')
        user = User.objects.create_user(username='func', password='x')
        funcionario = Employee.objects.create(user=user, delegation=delegacion, position=cargo, name='Func')
        self.activity = Activity.objects.create(
            number='ACT-1', employee=funcionario, delegation=delegacion, activity_type=tipo,
            date=datetime.date(2026, 6, 1), description='desc', evidence_code='EV-100',
        )
        Evidence.objects.create(unique_code='EVI-DUP', activity=self.activity)

    def test_codigo_unico_de_evidencia_no_se_repite(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Evidence.objects.create(unique_code='EVI-DUP', activity=self.activity)

    def test_codigo_se_genera_solo_cuando_viene_vacio(self):
        evidencia = Evidence.objects.create(activity=self.activity)
        self.assertTrue(evidencia.unique_code.startswith('EVI-'))

    def test_dos_evidencias_sin_codigo_no_chocan(self):
        primera = Evidence.objects.create(activity=self.activity)
        segunda = Evidence.objects.create(activity=self.activity)
        self.assertNotEqual(primera.unique_code, segunda.unique_code)

    def test_codigo_indicado_a_mano_se_respeta(self):
        evidencia = Evidence.objects.create(unique_code='EVI-MANUAL', activity=self.activity)
        self.assertEqual(evidencia.unique_code, 'EVI-MANUAL')


class RevisionEnVivoEvidenciasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_admin_sgr_ve_evidencias_de_ambas_delegaciones(self):
        self.client.login(username='admin_sgr', password=CLAVE_TEST)
        response = self.client.get('/admin/evidencias/evidence/')
        self.assertContains(response, 'EVID-CEN-001')
        self.assertContains(response, 'EVID-NOR-001')

    def test_funcionario_centro_no_ve_evidencias_de_norte(self):
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        response = self.client.get('/admin/evidencias/evidence/')
        self.assertContains(response, 'EVID-CEN-001')
        self.assertNotContains(response, 'EVID-NOR-001')

    def test_funcionario_centro_no_ve_la_accion_de_aprobar(self):
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        response = self.client.get('/admin/evidencias/evidence/')
        self.assertNotContains(response, 'Aprobar evidencias seleccionadas')

    def test_verificador_si_ve_la_accion_de_aprobar(self):
        self.client.login(username='verificador_leia', password=CLAVE_TEST)
        response = self.client.get('/admin/evidencias/evidence/')
        self.assertContains(response, 'Aprobar evidencias seleccionadas')
