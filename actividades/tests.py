import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Position, Delegation, Period, ActivityType
from funcionarios.models import Employee
from core.testing import CLAVE_TEST, sembrar_datos_demo

from .forms import ActividadForm
from .models import Activity, SocialCase


class ActividadFormTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Centro', address='Calle Falsa 123')
        self.position = Position.objects.create(name='Encargado Social')
        self.kind = ActivityType.objects.create(code='ATC-01', name='Atención ciudadana', category='service')
        self.user = User.objects.create_user(username='func1', password='x')
        self.employee = Employee.objects.create(
            user=self.user, delegation=self.delegation, position=self.position, name='Func Uno',
        )

    def _datos_base(self, **overrides):
        datos = {
            'number': 'ACT-2026-1',
            'employee': self.employee.pk,
            'delegation': self.delegation.pk,
            'activity_type': self.kind.pk,
            'date': datetime.date(2026, 6, 15),
            'description': 'Atención de vecino',
            'action': '',
            'contact': '',
            'phone': '',
            'is_agenda_item': False,
            'evidence_code': 'EV-001',
            'validation_status': 'pending',
        }
        datos.update(overrides)
        return datos

    def test_periodo_cerrado_bloquea_registro(self):
        periodo_cerrado = Period.objects.create(
            name='Cerrado', start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 3, 31), is_closed=True,
        )
        form = ActividadForm(data=self._datos_base(period=periodo_cerrado.pk))
        self.assertFalse(form.is_valid())
        # El error aparece una sola vez y junto al campo, no duplicado.
        self.assertEqual(form.errors['period'], ['Período cerrado: no se pueden registrar actividades.'])
        self.assertEqual(form.non_field_errors(), [])

    def test_codigo_evidencia_obligatorio(self):
        form = ActividadForm(data=self._datos_base(evidence_code=''))
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors['evidence_code']), 1)
        self.assertEqual(form.non_field_errors(), [])

    def test_actividad_valida_se_guarda(self):
        form = ActividadForm(data=self._datos_base())
        self.assertTrue(form.is_valid(), form.errors)


class AtencionSocialTests(TestCase):
    def setUp(self):
        delegacion = Delegation.objects.create(name='Norte', address='Av. Norte 456')
        cargo = Position.objects.create(name='Encargado Social 2')
        tipo = ActivityType.objects.create(code='SOC-04', name='Atención social', category='social')
        user = User.objects.create_user(username='func2', password='x')
        funcionario = Employee.objects.create(user=user, delegation=delegacion, position=cargo, name='Func Dos')
        self.activity = Activity.objects.create(
            number='ACT-2026-2', employee=funcionario, delegation=delegacion, activity_type=tipo,
            date=datetime.date(2026, 6, 1), description='Caso social', evidence_code='EV-002',
        )

    def test_no_permite_mas_de_tres_gestiones(self):
        for i in range(1, 4):
            SocialCase.objects.create(activity=self.activity, step_number=i, description=f'Gestión {i}')
        cuarta = SocialCase(activity=self.activity, step_number=4, description='Gestión 4')
        with self.assertRaises(ValidationError):
            cuarta.clean()


class ActividadUnicidadTests(TestCase):
    def setUp(self):
        self.delegation = Delegation.objects.create(name='Centro', address='Calle 1')
        cargo = Position.objects.create(name='Encargado')
        self.kind = ActivityType.objects.create(code='ATC-01', name='Atención', category='service')
        user = User.objects.create_user(username='func1', password='x')
        self.employee = Employee.objects.create(
            user=user, delegation=self.delegation, position=cargo, name='Func Uno',
        )
        Activity.objects.create(
            number='ACT-DUP', employee=self.employee, delegation=self.delegation,
            activity_type=self.kind, date=datetime.date(2026, 6, 1),
            description='Original', evidence_code='EV-DUP-1',
        )

    def test_numero_de_actividad_es_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Activity.objects.create(
                    number='ACT-DUP', employee=self.employee, delegation=self.delegation,
                    activity_type=self.kind, date=datetime.date(2026, 6, 2),
                    description='Duplicada', evidence_code='EV-DUP-2',
                )

    def test_codigo_evidencia_es_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Activity.objects.create(
                    number='ACT-OTRO', employee=self.employee, delegation=self.delegation,
                    activity_type=self.kind, date=datetime.date(2026, 6, 2),
                    description='Otra', evidence_code='EV-DUP-1',
                )


class RevisionEnVivoActividadesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_funcionario_centro_no_accede_a_actividad_de_norte_por_url(self):
        actividad_norte = Activity.objects.filter(delegation__name='Delegación Norte').first()
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        response = self.client.get(f'/admin/actividades/activity/{actividad_norte.pk}/change/')
        self.assertNotEqual(response.status_code, 200)

    def test_admin_sgr_ve_actividades_de_ambas_delegaciones(self):
        self.client.login(username='admin_sgr', password=CLAVE_TEST)
        response = self.client.get('/admin/actividades/activity/')
        self.assertContains(response, 'ACT-2026-001')
        self.assertContains(response, 'ACT-2026-005')

    def test_funcionario_centro_solo_ve_actividades_de_centro(self):
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        response = self.client.get('/admin/actividades/activity/')
        self.assertContains(response, 'ACT-2026-001')
        self.assertNotContains(response, 'ACT-2026-005')

    def _datos_formulario(self, **overrides):
        datos = {
            'number': 'ACT-NUEVA', 'period': '', 'date': '2026-07-10',
            'description': 'prueba', 'action': '', 'contact': '', 'phone': '',
            'evidence_code': 'EV-NUEVA', 'validation_status': 'approved',
            'atenciones_sociales-TOTAL_FORMS': '0', 'atenciones_sociales-INITIAL_FORMS': '0',
            'evidencias-TOTAL_FORMS': '0', 'evidencias-INITIAL_FORMS': '0',
        }
        datos.update(overrides)
        return datos

    def test_funcionario_centro_no_puede_crear_actividad_en_otra_delegacion(self):
        from core.models import Delegation
        from funcionarios.models import Employee

        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        norte = Delegation.objects.get(name='Delegación Norte')
        func_norte = Employee.objects.get(name='Carlos Rojas (Norte)')
        tipo_id = Activity.objects.first().activity_type_id

        self.client.post('/admin/actividades/activity/add/', self._datos_formulario(
            employee=func_norte.pk, delegation=norte.pk, activity_type=tipo_id,
        ), follow=True)

        self.assertFalse(Activity.objects.filter(number='ACT-NUEVA').exists())

    def test_funcionario_centro_no_puede_aprobar_su_propia_actividad(self):
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        actividad = Activity.objects.filter(
            delegation__name='Delegación Centro', validation_status='pending',
        ).first()

        self.client.post(f'/admin/actividades/activity/{actividad.pk}/change/', self._datos_formulario(
            number=actividad.number, employee=actividad.employee_id,
            delegation=actividad.delegation_id, activity_type=actividad.activity_type_id,
            date=actividad.date.isoformat(), description=actividad.description,
            evidence_code=actividad.evidence_code,
        ), follow=True)

        actividad.refresh_from_db()
        self.assertEqual(actividad.validation_status, 'pending')

    def test_autocomplete_de_funcionario_funciona_para_el_limitado(self):
        self.client.login(username='funcionario_centro', password=CLAVE_TEST)
        response = self.client.get('/admin/autocomplete/', {
            'term': '', 'app_label': 'actividades', 'model_name': 'activity', 'field_name': 'employee',
        })
        self.assertEqual(response.status_code, 200)
        nombres = [item['text'] for item in response.json()['results']]
        # Opción (a): el funcionario solo puede registrar actividades a su nombre.
        self.assertEqual(nombres, ['Ana Pérez (Centro)'])
