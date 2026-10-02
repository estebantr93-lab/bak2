"""Hallazgos de la auditoría de lógica: cada prueba falla con el código anterior a la corrección."""
import datetime
import io
import shutil
import struct
import tempfile
import zlib

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from actividades.models import Activity
from agenda.models import Commitment, CommitmentFollowUp
from colaboracion.admin import TrazaAuditoriaAdmin
from colaboracion.models import AuditLog
from core.models import Period
from core.testing import CLAVE_TEST, sembrar_datos_demo
from evidencias.forms import EvidenciaAdminForm
from evidencias.models import Evidence
from funcionarios.models import Employee, PasswordResetCode
from medicion.models import Goal

MEDIA_TEMPORAL = tempfile.mkdtemp()


def png(ancho=1, alto=1):
    """PNG válido; con ancho/alto grandes solo cambia lo que declara la cabecera (sigue pesando bytes)."""
    buffer = io.BytesIO()
    Image.new('RGB', (1, 1), (173, 0, 0)).save(buffer, format='PNG')
    datos = bytearray(buffer.getvalue())
    if (ancho, alto) != (1, 1):
        ihdr = struct.pack('>II', ancho, alto) + bytes(datos[24:29])
        datos[16:29] = ihdr
        datos[29:33] = struct.pack('>I', zlib.crc32(b'IHDR' + ihdr) & 0xffffffff)
    return bytes(datos)


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL, MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})
class AuditoriaLogicaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()
        cls.abierto = Period.objects.get(is_closed=False)
        cls.ana = Employee.objects.get(user__username='funcionario_centro')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def ingresar(self, username):
        self.assertTrue(self.client.login(username=username, password=CLAVE_TEST))

    def datos_actividad(self, actividad, **extra):
        datos = {
            'number': actividad.number, 'employee': actividad.employee_id, 'period': actividad.period_id,
            'activity_type': actividad.activity_type_id, 'date': actividad.date.isoformat(),
            'description': actividad.description, 'evidence_code': actividad.evidence_code,
        }
        datos.update(extra)
        return datos

    # --- Actividades -------------------------------------------------------------------------------
    def test_funcionario_no_modifica_una_actividad_ya_aprobada_pero_el_admin_si(self):
        aprobada = Activity.objects.filter(employee=self.ana, period=self.abierto).first()
        Activity.objects.filter(pk=aprobada.pk).update(validation_status='approved')
        self.ingresar('funcionario_centro')
        response = self.client.post(reverse('actividad_update', args=[aprobada.pk]),
                                    self.datos_actividad(aprobada, description='cambiada'))
        self.assertEqual(response.status_code, 403)
        self.ingresar('admin_centro')
        self.assertEqual(self.client.get(reverse('actividad_update', args=[aprobada.pk])).status_code, 200)

    def test_fecha_futura_o_fuera_del_periodo_no_se_acepta(self):
        actividad = Activity.objects.filter(employee=self.ana, period=self.abierto).first()
        actividad.date = timezone.localdate() + datetime.timedelta(days=1)
        with self.assertRaises(ValidationError) as futura:
            actividad.full_clean()
        self.assertIn('date', futura.exception.message_dict)
        actividad.date = self.abierto.start_date - datetime.timedelta(days=1)
        with self.assertRaises(ValidationError) as fuera:
            actividad.full_clean()
        self.assertIn('date', fuera.exception.message_dict)

    def test_estado_de_validacion_es_de_solo_lectura_en_el_admin_incluso_para_el_superusuario(self):
        self.ingresar('admin_sgr')
        actividad = Activity.objects.filter(period=self.abierto).first()
        response = self.client.get(f'/admin/actividades/activity/{actividad.pk}/change/')
        self.assertNotIn('validation_status', response.context['adminform'].form.fields)

    # --- Evidencias --------------------------------------------------------------------------------
    def test_admin_valida_el_archivo_igual_que_la_web(self):
        actividad = Activity.objects.filter(period=self.abierto).first()
        falso = SimpleUploadedFile('virus.pdf', b'MZ esto no es un PDF')
        form = EvidenciaAdminForm(data={'activity': actividad.pk, 'status': 'pending'}, files={'file': falso})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

    def test_imagen_que_declara_millones_de_pixeles_se_rechaza_sin_error_500(self):
        actividad = Activity.objects.filter(period=self.abierto).first()
        bomba = SimpleUploadedFile('foto.png', png(20000, 20000))
        form = EvidenciaAdminForm(data={'activity': actividad.pk, 'status': 'pending'}, files={'file': bomba})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

    def test_evidencia_en_linea_no_permite_cambiar_el_estado_sin_revisar(self):
        self.ingresar('admin_sgr')
        actividad = Activity.objects.filter(period=self.abierto).first()
        response = self.client.get(f'/admin/actividades/activity/{actividad.pk}/change/')
        inline = response.context['inline_admin_formsets'][0]
        self.assertNotIn('status', inline.formset.form.base_fields)

    def test_rechazar_exige_motivo(self):
        evidencia = Evidence.objects.create(activity=Activity.objects.filter(period=self.abierto).first(),
                                            description='Foto', file='evidencias/x.png')
        self.ingresar('verificador_leia')
        response = self.client.post(reverse('evidencia_update', args=[evidencia.pk]),
                                    {'description': 'Foto', 'status': 'rejected', 'result': ''})
        self.assertIn('result', response.context['form'].errors)
        evidencia.refresh_from_db()
        self.assertEqual(evidencia.status, 'pending')

    def test_verificador_revisa_sin_reasignar_la_evidencia(self):
        actividades = list(Activity.objects.filter(period=self.abierto)[:2])
        evidencia = Evidence.objects.create(activity=actividades[0], description='Foto', file='evidencias/x.png')
        self.ingresar('verificador_leia')
        response = self.client.post(reverse('evidencia_update', args=[evidencia.pk]), {
            'activity': actividades[1].pk, 'description': 'otra', 'status': 'approved', 'result': 'Correcta',
        })
        self.assertEqual(response.status_code, 302)
        evidencia.refresh_from_db()
        self.assertEqual((evidencia.activity_id, evidencia.description, evidencia.status),
                         (actividades[0].pk, 'Foto', 'approved'))

    # --- Compromisos -------------------------------------------------------------------------------
    def test_seguimiento_actualiza_el_estado_del_compromiso(self):
        compromiso = Commitment.objects.exclude(status='done').first()
        CommitmentFollowUp.objects.create(commitment=compromiso, new_status='done', description='Terminado en terreno')
        compromiso.refresh_from_db()
        self.assertEqual(compromiso.status, 'done')
        self.assertTrue(compromiso.notes)  # un compromiso realizado siempre queda con observaciones
        compromiso.full_clean()

    def test_dashboard_cuenta_los_compromisos_sin_responsable(self):
        delegacion = self.ana.delegation
        Commitment.objects.create(title='Sin asignar vencido', delegation=delegacion,
                                  due_date=timezone.localdate() - datetime.timedelta(days=3), status='pending')
        self.ingresar('admin_centro')
        response = self.client.get(reverse('dashboard'))
        esperados = Commitment.objects.filter(delegation=delegacion, due_date__lt=timezone.localdate()) \
            .exclude(status='done').count()
        self.assertEqual(response.context['totales']['comp_vencidos'], esperados)

    # --- Metas -------------------------------------------------------------------------------------
    def test_metas_de_un_periodo_cerrado_no_se_modifican(self):
        meta = Goal.objects.filter(period=self.abierto).first()
        meta.period = Period.objects.get(is_closed=True)
        with self.assertRaises(ValidationError) as error:
            meta.full_clean()
        self.assertIn('period', error.exception.message_dict)

    # --- Acceso y recuperación ---------------------------------------------------------------------
    def test_funcionario_desactivado_no_entra_ni_con_sesion_abierta(self):
        self.ingresar('funcionario_centro')
        Employee.objects.filter(pk=self.ana.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 403)
        self.client.logout()
        response = self.client.post(reverse('login'), {'username': 'funcionario_centro', 'password': CLAVE_TEST})
        # Mismo mensaje que una clave incorrecta; el motivo queda en la traza para el administrador.
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertNotContains(response, 'desactivado')

    def test_recuperacion_limita_los_codigos_por_hora(self):
        correo = User.objects.get(username='funcionario_centro').email
        for _ in range(8):
            self.client.post(reverse('recuperar_solicitar'), {'email': correo})
        self.assertEqual(PasswordResetCode.objects.filter(user__email=correo).count(), 5)
        self.assertEqual(len(mail.outbox), 5)

    # --- Auditoría ---------------------------------------------------------------------------------
    def test_traza_de_auditoria_es_de_solo_lectura(self):
        from django.contrib import admin
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        request.user = User.objects.get(username='admin_sgr')
        modelo_admin = TrazaAuditoriaAdmin(AuditLog, admin.site)
        self.assertFalse(modelo_admin.has_add_permission(request))
        self.assertFalse(modelo_admin.has_change_permission(request))
        self.assertFalse(modelo_admin.has_delete_permission(request))
