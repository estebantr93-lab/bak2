from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from actividades.forms import ActividadWebForm
from actividades.models import Activity, SocialCase
from agenda.models import Commitment
from core.testing import CLAVE_TEST, sembrar_datos_demo
from evidencias.models import Evidence


class BorradoLogicoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def setUp(self):
        self.activity = Activity.objects.filter(delegation__name='Delegación Centro').first()

    def test_delete_marca_deleted_at_y_no_borra_la_fila(self):
        self.activity.delete()
        self.assertFalse(Activity.objects.filter(pk=self.activity.pk).exists())
        self.assertTrue(Activity.all_objects.filter(pk=self.activity.pk, deleted_at__isnull=False).exists())

    def test_el_borrado_se_propaga_a_evidencias_y_atenciones(self):
        Evidence.objects.create(activity=self.activity, description='x')
        SocialCase.objects.create(activity=self.activity, step_number=3, description='x')
        self.activity.delete()
        self.assertFalse(Evidence.objects.filter(activity=self.activity).exists())
        self.assertFalse(SocialCase.objects.filter(activity=self.activity).exists())
        self.assertTrue(Evidence.all_objects.filter(activity=self.activity).exists())

    def test_queryset_delete_tambien_es_logico(self):
        total = Commitment.objects.count()
        Commitment.objects.all().delete()
        self.assertEqual(Commitment.objects.count(), 0)
        self.assertEqual(Commitment.all_objects.count(), total)

    def test_restore_devuelve_el_registro(self):
        self.activity.delete()
        Activity.all_objects.get(pk=self.activity.pk).restore()
        self.assertTrue(Activity.objects.filter(pk=self.activity.pk).exists())

    def test_numero_de_actividad_eliminada_no_provoca_error_500(self):
        numero = self.activity.number
        self.activity.delete()
        user = User.objects.get(username='admin_centro')
        form = ActividadWebForm(user=user, data={
            'number': numero, 'employee': self.activity.employee_id,
            'period': self.activity.period_id, 'activity_type': self.activity.activity_type_id,
            'date': '2026-07-15', 'description': 'x', 'evidence_code': 'NUEVO-001',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('number', form.errors)

    def test_listados_admin_y_dashboard_no_muestran_eliminados(self):
        self.activity.delete()
        self.client.login(username='admin_centro', password=CLAVE_TEST)
        response = self.client.get(reverse('actividad_list'))
        self.assertNotIn(self.activity, list(response.context['activities']))
        response = self.client.get('/admin/actividades/activity/')
        self.assertNotIn(self.activity, list(response.context['cl'].queryset))
        response = self.client.get(reverse('dashboard'))
        total = Activity.objects.filter(delegation__name='Delegación Centro', period__is_closed=False).count()
        self.assertEqual(response.context['totales']['act_total'], total)

    def test_eliminar_desde_el_admin_es_logico(self):
        self.client.login(username='admin_sgr', password=CLAVE_TEST)
        self.client.post(f'/admin/actividades/activity/{self.activity.pk}/delete/', {'post': 'yes'})
        self.assertTrue(Activity.all_objects.filter(pk=self.activity.pk, deleted_at__isnull=False).exists())
