"""Revisión de evidencias: todas las vías usan registrar_revision y el estado de la actividad se deriva."""
import datetime

from django.test import TestCase
from django.urls import reverse

from actividades.models import Activity
from colaboracion.models import AuditLog
from core.models import ActivityType, Period
from core.testing import SesionTestMixin, sembrar_datos_demo
from evidencias.models import Evidence, Validation
from evidencias.services import sincronizar_estado_actividades
from funcionarios.models import Employee


class BaseRevision(SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()
        cls.ana = Employee.objects.get(name='Ana Pérez (Centro)')
        tipo = ActivityType.objects.get(code='ATC-01')
        cls.abierto = Period.objects.get(is_closed=False)
        cls.cerrado = Period.objects.get(is_closed=True)
        cls.actividad = Activity.objects.create(
            number='REV-001', employee=cls.ana, delegation=cls.ana.delegation, period=cls.abierto,
            activity_type=tipo, date=datetime.date(2026, 7, 5), description='A revisar', evidence_code='EV-REV-001',
        )
        cls.cerrada = Activity.objects.create(
            number='REV-CERR', employee=cls.ana, delegation=cls.ana.delegation, period=cls.cerrado,
            activity_type=tipo, date=datetime.date(2026, 2, 5), description='Cerrada', evidence_code='EV-REV-CERR',
        )

    def setUp(self):
        self.evidencia = Evidence.objects.create(activity=self.actividad, description='respaldo')
        self.evidencia.file.name = 'evidencias/respaldo.pdf'
        self.evidencia.save(update_fields=['file'])

    def assert_revisada(self, estado, revisor):
        self.evidencia.refresh_from_db()
        self.actividad.refresh_from_db()
        self.assertEqual(self.evidencia.status, estado)
        self.assertEqual(self.evidencia.reviewed_by.username, revisor)
        self.assertTrue(Validation.objects.filter(evidence=self.evidencia, status=estado, reviewer__username=revisor).exists())
        self.assertTrue(AuditLog.objects.filter(action=f'evidencia_{estado}', entity_id=self.evidencia.pk).exists())
        self.assertEqual(self.actividad.validation_status, estado)


class ViasDeRevisionTests(BaseRevision):
    def test_web_verificador_aprueba_y_la_actividad_queda_aprobada(self):
        self.ingresar('verificador_leia')
        self.client.post(reverse('evidencia_update', args=[self.evidencia.pk]), {
            'activity': self.actividad.pk, 'description': 'respaldo', 'status': 'approved', 'result': 'conforme',
        })
        self.assert_revisada('approved', 'verificador_leia')

    def test_web_verificador_rechaza_y_la_actividad_queda_rechazada(self):
        self.ingresar('verificador_leia')
        self.client.post(reverse('evidencia_update', args=[self.evidencia.pk]), {
            'activity': self.actividad.pk, 'description': 'respaldo', 'status': 'rejected', 'result': 'ilegible',
        })
        self.assert_revisada('rejected', 'verificador_leia')

    def test_admin_formulario_de_cambio_registra_revisor_y_validacion(self):
        self.ingresar('verificador_leia')
        self.client.post(f'/admin/evidencias/evidence/{self.evidencia.pk}/change/', {
            'activity': self.actividad.pk, 'description': 'respaldo', 'status': 'approved', 'result': 'admin',
        })
        self.assert_revisada('approved', 'verificador_leia')

    def test_admin_alta_de_validacion_actualiza_evidencia_y_actividad(self):
        self.ingresar('admin_centro')
        response = self.client.post('/admin/evidencias/validation/add/', {
            'evidence': self.evidencia.pk, 'status': 'approved', 'comment': 'desde validaciones',
        })
        self.assertEqual(response.status_code, 302)
        self.assert_revisada('approved', 'admin_centro')

    def test_admin_accion_masiva(self):
        self.ingresar('verificador_leia')
        self.client.post('/admin/evidencias/evidence/', {
            'action': 'aprobar_evidencias', '_selected_action': [self.evidencia.pk],
        })
        self.assert_revisada('approved', 'verificador_leia')

    def test_validacion_no_se_edita_despues(self):
        self.ingresar('admin_sgr')
        self.client.post('/admin/evidencias/validation/add/', {'evidence': self.evidencia.pk, 'status': 'approved', 'comment': 'x'})
        validacion = Validation.objects.get(evidence=self.evidencia)
        response = self.client.post(f'/admin/evidencias/validation/{validacion.pk}/change/', {'status': 'rejected'})
        self.assertEqual(response.status_code, 403)

    def test_eliminar_la_evidencia_recalcula_la_actividad(self):
        self.ingresar('verificador_leia')
        self.client.post(reverse('evidencia_update', args=[self.evidencia.pk]), {
            'activity': self.actividad.pk, 'description': 'respaldo', 'status': 'approved', 'result': 'ok',
        })
        self.evidencia.delete()
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.validation_status, 'pending')

    def test_aprobar_mueve_el_dashboard(self):
        self.ingresar('admin_centro')
        antes = self.client.get(reverse('dashboard')).context['totales']['act_aprobadas']
        self.client.logout()
        self.ingresar('verificador_leia')
        self.client.post(reverse('evidencia_update', args=[self.evidencia.pk]), {
            'activity': self.actividad.pk, 'description': 'respaldo', 'status': 'approved', 'result': 'ok',
        })
        self.client.logout()
        self.ingresar('admin_centro')
        despues = self.client.get(reverse('dashboard')).context['totales']['act_aprobadas']
        self.assertEqual(despues, antes + 1)


class PeriodoCerradoCongelaLoDependienteTests(BaseRevision):
    def test_admin_no_agrega_evidencia_a_actividad_cerrada_ni_siquiera_el_superusuario(self):
        for username in ('admin_centro', 'admin_sgr'):
            self.ingresar(username)
            self.client.post('/admin/evidencias/evidence/add/', {
                'activity': self.cerrada.pk, 'description': f'post-cierre {username}', 'status': 'pending',
            })
            self.assertFalse(Evidence.all_objects.filter(description=f'post-cierre {username}').exists(), username)

    def test_evidencia_de_actividad_cerrada_no_se_edita_ni_elimina(self):
        evidencia = Evidence.objects.create(activity=self.cerrada, description='histórica')
        self.ingresar('admin_centro')
        self.assertEqual(self.client.post(reverse('evidencia_delete', args=[evidencia.pk])).status_code, 403)
        self.assertEqual(self.client.post(f'/admin/evidencias/evidence/{evidencia.pk}/delete/', {'post': 'yes'}).status_code, 403)
        self.assertIsNone(Evidence.all_objects.get(pk=evidencia.pk).deleted_at)

    def test_formularios_web_no_ofrecen_actividades_cerradas(self):
        self.ingresar('funcionario_centro')
        for nombre in ('evidencia_create', 'atencion_create'):
            opciones = self.client.get(reverse(nombre)).context['form'].fields['activity'].queryset
            self.assertFalse(opciones.filter(period__is_closed=True).exists(), nombre)

    def test_accion_masiva_omite_evidencias_de_periodo_cerrado(self):
        evidencia = Evidence.objects.create(activity=self.cerrada, description='histórica')
        self.ingresar('verificador_leia')
        self.client.post('/admin/evidencias/evidence/', {'action': 'aprobar_evidencias', '_selected_action': [evidencia.pk]})
        self.assertEqual(Evidence.objects.get(pk=evidencia.pk).status, 'pending')


class DatosDeCargaConsistentesTests(TestCase):
    def test_estado_de_cada_actividad_coincide_con_sus_evidencias(self):
        sembrar_datos_demo()
        antes = dict(Activity.all_objects.values_list('pk', 'validation_status'))
        sincronizar_estado_actividades(Activity.all_objects.all())
        self.assertEqual(antes, dict(Activity.all_objects.values_list('pk', 'validation_status')))
