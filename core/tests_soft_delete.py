from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from actividades.forms import ActividadWebForm
from actividades.models import Actividad, AtencionSocial
from agenda.models import Compromiso
from core.testing import CLAVE_TEST, sembrar_datos_demo
from evidencias.models import Evidencia


class BorradoLogicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def setUp(self):
        self.actividad = Actividad.objects.filter(delegacion__nombre='Delegación Centro').first()

    def test_delete_marca_deleted_at_y_no_borra_la_fila(self):
        self.actividad.delete()
        self.assertFalse(Actividad.objects.filter(pk=self.actividad.pk).exists())
        self.assertTrue(Actividad.all_objects.filter(pk=self.actividad.pk, deleted_at__isnull=False).exists())

    def test_el_borrado_se_propaga_a_evidencias_y_atenciones(self):
        Evidencia.objects.create(actividad=self.actividad, descripcion='x')
        AtencionSocial.objects.create(actividad=self.actividad, numero_gestion=3, descripcion='x')
        self.actividad.delete()
        self.assertFalse(Evidencia.objects.filter(actividad=self.actividad).exists())
        self.assertFalse(AtencionSocial.objects.filter(actividad=self.actividad).exists())
        self.assertTrue(Evidencia.all_objects.filter(actividad=self.actividad).exists())

    def test_queryset_delete_tambien_es_logico(self):
        total = Compromiso.objects.count()
        Compromiso.objects.all().delete()
        self.assertEqual(Compromiso.objects.count(), 0)
        self.assertEqual(Compromiso.all_objects.count(), total)

    def test_restore_devuelve_el_registro(self):
        self.actividad.delete()
        Actividad.all_objects.get(pk=self.actividad.pk).restore()
        self.assertTrue(Actividad.objects.filter(pk=self.actividad.pk).exists())

    def test_numero_de_actividad_eliminada_no_provoca_error_500(self):
        numero = self.actividad.numero
        self.actividad.delete()
        user = User.objects.get(username='admin_centro')
        form = ActividadWebForm(user=user, data={
            'numero': numero, 'funcionario': self.actividad.funcionario_id,
            'periodo': self.actividad.periodo_id, 'tipo_actividad': self.actividad.tipo_actividad_id,
            'fecha': '2026-07-15', 'descripcion': 'x', 'codigo_evidencia': 'NUEVO-001',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('numero', form.errors)

    def test_listados_admin_y_dashboard_no_muestran_eliminados(self):
        self.actividad.delete()
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        response = self.client.get(reverse('actividad_list'))
        self.assertNotIn(self.actividad, list(response.context['actividades']))
        response = self.client.get('/admin/actividades/actividad/')
        self.assertNotIn(self.actividad, list(response.context['cl'].queryset))
        response = self.client.get(reverse('dashboard'))
        total = Actividad.objects.filter(delegacion__nombre='Delegación Centro', periodo__cerrado=False).count()
        self.assertEqual(response.context['totales']['act_total'], total)

    def test_eliminar_desde_el_admin_es_logico(self):
        self.client.login(username='admin_sgr', password=CLAVE_TEST)
        self.client.post(f'/admin/actividades/actividad/{self.actividad.pk}/delete/', {'post': 'yes'})
        self.assertTrue(Actividad.all_objects.filter(pk=self.actividad.pk, deleted_at__isnull=False).exists())
