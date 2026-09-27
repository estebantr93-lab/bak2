from django.test import TestCase
from django.urls import reverse

from core.testing import CLAVE_TEST, sembrar_datos_demo
from evidencias.models import Evidence, Validation
from funcionarios.models import Employee


class AuditoriaRubricaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def ingresar(self, username):
        self.assertTrue(self.client.login(username=username, password=CLAVE_TEST))

    def test_admin_de_delegacion_no_ve_la_otra_ni_en_los_filtros(self):
        self.ingresar('admin_centro')
        for url in ['/admin/actividades/activity/', '/admin/evidencias/evidence/', '/admin/agenda/commitment/',
                    '/admin/funcionarios/employee/', '/admin/medicion/indicator/']:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertNotContains(response, 'Delegación Norte', msg_prefix=url)

    def test_superusuario_si_filtra_por_ambas_delegaciones(self):
        self.ingresar('admin_sgr')
        response = self.client.get('/admin/actividades/activity/')
        self.assertContains(response, 'Delegación Norte')

    def test_password_reset_de_django_redirige_al_flujo_de_codigo(self):
        for url in ['/accounts/password_reset/', '/accounts/password_reset/done/', '/accounts/reset/abc/def-123/']:
            self.assertRedirects(self.client.get(url), reverse('recuperar_solicitar'), msg_prefix=url)

    def test_validaciones_de_evidencias_eliminadas_no_se_listan(self):
        self.ingresar('admin_sgr')
        validacion = Validation.objects.first()
        Evidence.objects.get(pk=validacion.evidence_id).delete()
        response = self.client.get('/admin/evidencias/validation/')
        self.assertNotIn(validacion, list(response.context['cl'].queryset))

    def test_funcionario_no_se_borra_fisicamente_desde_el_admin(self):
        self.ingresar('admin_sgr')
        empleado = Employee.objects.get(name='Ana Pérez (Centro)')
        response = self.client.get(f'/admin/funcionarios/employee/{empleado.pk}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Employee.objects.filter(pk=empleado.pk).exists())
