import datetime
from io import StringIO

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import RequestFactory, TestCase

from core.models import Cargo, Delegacion, TipoActividad
from funcionarios.models import Funcionario
from actividades.models import Actividad

from .admin import EvidenciaAdmin
from .models import Evidencia, Validacion


class AprobarEvidenciasActionTests(TestCase):
    def setUp(self):
        delegacion = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        cargo = Cargo.objects.create(nombre='Verificador')
        tipo = TipoActividad.objects.create(codigo='ATC-01', nombre='Atención', categoria='atencion')
        func_user = User.objects.create_user(username='func', password='x')
        funcionario = Funcionario.objects.create(user=func_user, delegacion=delegacion, cargo=cargo, nombre='Func')
        actividad = Actividad.objects.create(
            numero='ACT-1', funcionario=funcionario, delegacion=delegacion, tipo_actividad=tipo,
            fecha=datetime.date(2026, 6, 1), descripcion='desc', codigo_evidencia='EV-100',
        )
        self.evidencia = Evidencia.objects.create(codigo_unico='EVI-001', actividad=actividad)

        ct = ContentType.objects.get_for_model(Evidencia)
        self.permiso_aprobar = Permission.objects.get(content_type=ct, codename='can_approve_evidencia')
        self.verificador = User.objects.create_user(username='verificador', password='x', is_staff=True)
        self.verificador.user_permissions.add(self.permiso_aprobar)

        self.sin_permiso = User.objects.create_user(username='sinpermiso', password='x', is_staff=True)

        self.factory = RequestFactory()

    def _request_con_mensajes(self, usuario):
        request = self.factory.post('/admin/evidencias/evidencia/')
        request.user = usuario
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_aprobar_evidencias_cambia_estado_y_crea_validacion(self):
        request = self._request_con_mensajes(self.verificador)
        admin_instance = EvidenciaAdmin(Evidencia, None)

        admin_instance.aprobar_evidencias(request, Evidencia.objects.filter(pk=self.evidencia.pk))

        self.evidencia.refresh_from_db()
        self.assertEqual(self.evidencia.estado, 'aprobada')
        self.assertEqual(self.evidencia.revisada_por, self.verificador)
        self.assertTrue(Validacion.objects.filter(evidencia=self.evidencia, estado='aprobada').exists())

    def test_usuario_sin_permiso_no_puede_aprobar(self):
        request = self._request_con_mensajes(self.sin_permiso)
        admin_instance = EvidenciaAdmin(Evidencia, None)

        admin_instance.aprobar_evidencias(request, Evidencia.objects.filter(pk=self.evidencia.pk))

        self.evidencia.refresh_from_db()
        self.assertEqual(self.evidencia.estado, 'pendiente')
        self.assertFalse(Validacion.objects.filter(evidencia=self.evidencia).exists())


class EvidenciaUnicidadTests(TestCase):
    def setUp(self):
        delegacion = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        cargo = Cargo.objects.create(nombre='Encargado')
        tipo = TipoActividad.objects.create(codigo='ATC-01', nombre='Atención', categoria='atencion')
        user = User.objects.create_user(username='func', password='x')
        funcionario = Funcionario.objects.create(user=user, delegacion=delegacion, cargo=cargo, nombre='Func')
        self.actividad = Actividad.objects.create(
            numero='ACT-1', funcionario=funcionario, delegacion=delegacion, tipo_actividad=tipo,
            fecha=datetime.date(2026, 6, 1), descripcion='desc', codigo_evidencia='EV-100',
        )
        Evidencia.objects.create(codigo_unico='EVI-DUP', actividad=self.actividad)

    def test_codigo_unico_de_evidencia_no_se_repite(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Evidencia.objects.create(codigo_unico='EVI-DUP', actividad=self.actividad)

    def test_codigo_se_genera_solo_cuando_viene_vacio(self):
        evidencia = Evidencia.objects.create(actividad=self.actividad)
        self.assertTrue(evidencia.codigo_unico.startswith('EVI-'))

    def test_dos_evidencias_sin_codigo_no_chocan(self):
        primera = Evidencia.objects.create(actividad=self.actividad)
        segunda = Evidencia.objects.create(actividad=self.actividad)
        self.assertNotEqual(primera.codigo_unico, segunda.codigo_unico)

    def test_codigo_indicado_a_mano_se_respeta(self):
        evidencia = Evidencia.objects.create(codigo_unico='EVI-MANUAL', actividad=self.actividad)
        self.assertEqual(evidencia.codigo_unico, 'EVI-MANUAL')


class RevisionEnVivoEvidenciasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def test_admin_sgr_ve_evidencias_de_ambas_delegaciones(self):
        self.client.login(username='admin_sgr', password='Admin#2026SGR')
        response = self.client.get('/admin/evidencias/evidencia/')
        self.assertContains(response, 'EVID-CEN-001')
        self.assertContains(response, 'EVID-NOR-001')

    def test_funcionario_centro_no_ve_evidencias_de_norte(self):
        self.client.login(username='funcionario_centro', password='Centro#2026SGR')
        response = self.client.get('/admin/evidencias/evidencia/')
        self.assertContains(response, 'EVID-CEN-001')
        self.assertNotContains(response, 'EVID-NOR-001')

    def test_funcionario_centro_no_ve_la_accion_de_aprobar(self):
        self.client.login(username='funcionario_centro', password='Centro#2026SGR')
        response = self.client.get('/admin/evidencias/evidencia/')
        self.assertNotContains(response, 'Aprobar evidencias seleccionadas')

    def test_verificador_si_ve_la_accion_de_aprobar(self):
        self.client.login(username='verificador_leia', password='Verifica#2026SGR')
        response = self.client.get('/admin/evidencias/evidencia/')
        self.assertContains(response, 'Aprobar evidencias seleccionadas')
