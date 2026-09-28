from django.test import TestCase
from django.urls import reverse

from core.testing import SesionTestMixin, sembrar_datos_demo
from evidencias.models import Evidence, Validation
from funcionarios.models import Employee


class AuditoriaRubricaTests(SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

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

    def test_validaciones_de_evidencias_eliminadas_solo_las_ve_el_superadmin(self):
        validacion = Validation.objects.filter(evidence__activity__delegation__name='Delegación Centro').first()
        Evidence.objects.get(pk=validacion.evidence_id).delete()
        # Regla de negocio: el administrador general sigue viendo lo eliminado (marcado) y lo puede filtrar.
        self.ingresar('admin_sgr')
        self.assertIn(validacion, list(self.client.get('/admin/evidencias/validation/').context['cl'].queryset))
        activos = self.client.get('/admin/evidencias/validation/', {'registro': 'activos'})
        self.assertNotIn(validacion, list(activos.context['cl'].queryset))
        # Un administrador de delegación ya no la ve.
        self.ingresar('admin_centro')
        self.assertNotIn(validacion, list(self.client.get('/admin/evidencias/validation/').context['cl'].queryset))

    def test_funcionario_no_se_borra_fisicamente_desde_el_admin(self):
        self.ingresar('admin_sgr')
        empleado = Employee.objects.get(name='Ana Pérez (Centro)')
        response = self.client.get(f'/admin/funcionarios/employee/{empleado.pk}/delete/')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Employee.objects.filter(pk=empleado.pk).exists())

    def test_superusuario_puede_borrar_un_usuario_con_perfil_sin_historial(self):
        from django.contrib.auth.models import User

        from core.models import Delegation, Position

        user = User.objects.create_user(username='temporal', password='x')
        Employee.objects.create(
            user=user, delegation=Delegation.objects.first(), position=Position.objects.first(), name='Temporal',
        )
        self.ingresar('admin_sgr')
        response = self.client.post(f'/admin/auth/user/{user.pk}/delete/', {'post': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertFalse(Employee.objects.filter(name='Temporal').exists())

    def test_admin_de_funcionarios_no_ofrece_borrado_masivo(self):
        self.ingresar('admin_sgr')
        response = self.client.get('/admin/funcionarios/employee/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'delete_selected')
