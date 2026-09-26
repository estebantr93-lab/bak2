import datetime
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Cargo, Delegacion, Periodo, TipoActividad
from funcionarios.models import Funcionario

from .forms import ActividadForm
from .models import Actividad, AtencionSocial


class ActividadFormTests(TestCase):
    def setUp(self):
        self.delegacion = Delegacion.objects.create(nombre='Centro', direccion='Calle Falsa 123')
        self.cargo = Cargo.objects.create(nombre='Encargado Social')
        self.tipo = TipoActividad.objects.create(codigo='ATC-01', nombre='Atención ciudadana', categoria='atencion')
        self.user = User.objects.create_user(username='func1', password='x')
        self.funcionario = Funcionario.objects.create(
            user=self.user, delegacion=self.delegacion, cargo=self.cargo, nombre='Func Uno',
        )

    def _datos_base(self, **overrides):
        datos = {
            'numero': 'ACT-2026-1',
            'funcionario': self.funcionario.pk,
            'delegacion': self.delegacion.pk,
            'tipo_actividad': self.tipo.pk,
            'fecha': datetime.date(2026, 6, 15),
            'descripcion': 'Atención de vecino',
            'accion': '',
            'contacto': '',
            'telefono': '',
            'indicador_agenda': False,
            'codigo_evidencia': 'EV-001',
            'estado_validacion': 'pendiente',
        }
        datos.update(overrides)
        return datos

    def test_periodo_cerrado_bloquea_registro(self):
        periodo_cerrado = Periodo.objects.create(
            nombre='Cerrado', fecha_inicio=datetime.date(2026, 1, 1),
            fecha_termino=datetime.date(2026, 3, 31), cerrado=True,
        )
        form = ActividadForm(data=self._datos_base(periodo=periodo_cerrado.pk))
        self.assertFalse(form.is_valid())

    def test_codigo_evidencia_obligatorio(self):
        form = ActividadForm(data=self._datos_base(codigo_evidencia=''))
        self.assertFalse(form.is_valid())

    def test_actividad_valida_se_guarda(self):
        form = ActividadForm(data=self._datos_base())
        self.assertTrue(form.is_valid(), form.errors)


class AtencionSocialTests(TestCase):
    def setUp(self):
        delegacion = Delegacion.objects.create(nombre='Norte', direccion='Av. Norte 456')
        cargo = Cargo.objects.create(nombre='Encargado Social 2')
        tipo = TipoActividad.objects.create(codigo='SOC-04', nombre='Atención social', categoria='social')
        user = User.objects.create_user(username='func2', password='x')
        funcionario = Funcionario.objects.create(user=user, delegacion=delegacion, cargo=cargo, nombre='Func Dos')
        self.actividad = Actividad.objects.create(
            numero='ACT-2026-2', funcionario=funcionario, delegacion=delegacion, tipo_actividad=tipo,
            fecha=datetime.date(2026, 6, 1), descripcion='Caso social', codigo_evidencia='EV-002',
        )

    def test_no_permite_mas_de_tres_gestiones(self):
        for i in range(1, 4):
            AtencionSocial.objects.create(actividad=self.actividad, numero_gestion=i, descripcion=f'Gestión {i}')
        cuarta = AtencionSocial(actividad=self.actividad, numero_gestion=4, descripcion='Gestión 4')
        with self.assertRaises(ValidationError):
            cuarta.clean()


class ActividadUnicidadTests(TestCase):
    def setUp(self):
        self.delegacion = Delegacion.objects.create(nombre='Centro', direccion='Calle 1')
        cargo = Cargo.objects.create(nombre='Encargado')
        self.tipo = TipoActividad.objects.create(codigo='ATC-01', nombre='Atención', categoria='atencion')
        user = User.objects.create_user(username='func1', password='x')
        self.funcionario = Funcionario.objects.create(
            user=user, delegacion=self.delegacion, cargo=cargo, nombre='Func Uno',
        )
        Actividad.objects.create(
            numero='ACT-DUP', funcionario=self.funcionario, delegacion=self.delegacion,
            tipo_actividad=self.tipo, fecha=datetime.date(2026, 6, 1),
            descripcion='Original', codigo_evidencia='EV-DUP-1',
        )

    def test_numero_de_actividad_es_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Actividad.objects.create(
                    numero='ACT-DUP', funcionario=self.funcionario, delegacion=self.delegacion,
                    tipo_actividad=self.tipo, fecha=datetime.date(2026, 6, 2),
                    descripcion='Duplicada', codigo_evidencia='EV-DUP-2',
                )

    def test_codigo_evidencia_es_unico(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Actividad.objects.create(
                    numero='ACT-OTRO', funcionario=self.funcionario, delegacion=self.delegacion,
                    tipo_actividad=self.tipo, fecha=datetime.date(2026, 6, 2),
                    descripcion='Otra', codigo_evidencia='EV-DUP-1',
                )


class RevisionEnVivoActividadesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def test_funcionario_centro_no_accede_a_actividad_de_norte_por_url(self):
        actividad_norte = Actividad.objects.filter(delegacion__nombre='Delegación Norte').first()
        self.client.login(username='funcionario_centro', password='Centro#2026SGR')
        response = self.client.get(f'/admin/actividades/actividad/{actividad_norte.pk}/change/')
        self.assertNotEqual(response.status_code, 200)

    def test_admin_sgr_ve_actividades_de_ambas_delegaciones(self):
        self.client.login(username='admin_sgr', password='Admin#2026SGR')
        response = self.client.get('/admin/actividades/actividad/')
        self.assertContains(response, 'ACT-2026-001')
        self.assertContains(response, 'ACT-2026-005')

    def test_funcionario_centro_solo_ve_actividades_de_centro(self):
        self.client.login(username='funcionario_centro', password='Centro#2026SGR')
        response = self.client.get('/admin/actividades/actividad/')
        self.assertContains(response, 'ACT-2026-001')
        self.assertNotContains(response, 'ACT-2026-005')

    def _datos_formulario(self, **overrides):
        datos = {
            'numero': 'ACT-NUEVA', 'periodo': '', 'fecha': '2026-07-10',
            'descripcion': 'prueba', 'accion': '', 'contacto': '', 'telefono': '',
            'codigo_evidencia': 'EV-NUEVA', 'estado_validacion': 'aprobada',
            'atenciones_sociales-TOTAL_FORMS': '0', 'atenciones_sociales-INITIAL_FORMS': '0',
            'evidencias-TOTAL_FORMS': '0', 'evidencias-INITIAL_FORMS': '0',
        }
        datos.update(overrides)
        return datos

    def test_funcionario_centro_no_puede_crear_actividad_en_otra_delegacion(self):
        from core.models import Delegacion
        from funcionarios.models import Funcionario

        self.client.login(username='funcionario_centro', password='Centro#2026SGR')
        norte = Delegacion.objects.get(nombre='Delegación Norte')
        func_norte = Funcionario.objects.get(nombre='Carlos Rojas (Norte)')
        tipo_id = Actividad.objects.first().tipo_actividad_id

        self.client.post('/admin/actividades/actividad/add/', self._datos_formulario(
            funcionario=func_norte.pk, delegacion=norte.pk, tipo_actividad=tipo_id,
        ), follow=True)

        self.assertFalse(Actividad.objects.filter(numero='ACT-NUEVA').exists())

    def test_funcionario_centro_no_puede_aprobar_su_propia_actividad(self):
        self.client.login(username='funcionario_centro', password='Centro#2026SGR')
        actividad = Actividad.objects.filter(
            delegacion__nombre='Delegación Centro', estado_validacion='pendiente',
        ).first()

        self.client.post(f'/admin/actividades/actividad/{actividad.pk}/change/', self._datos_formulario(
            numero=actividad.numero, funcionario=actividad.funcionario_id,
            delegacion=actividad.delegacion_id, tipo_actividad=actividad.tipo_actividad_id,
            fecha=actividad.fecha.isoformat(), descripcion=actividad.descripcion,
            codigo_evidencia=actividad.codigo_evidencia,
        ), follow=True)

        actividad.refresh_from_db()
        self.assertEqual(actividad.estado_validacion, 'pendiente')

    def test_autocomplete_de_funcionario_funciona_para_el_limitado(self):
        self.client.login(username='funcionario_centro', password='Centro#2026SGR')
        response = self.client.get('/admin/autocomplete/', {
            'term': '', 'app_label': 'actividades', 'model_name': 'actividad', 'field_name': 'funcionario',
        })
        self.assertEqual(response.status_code, 200)
        nombres = [item['text'] for item in response.json()['results']]
        self.assertEqual(nombres, ['Ana Pérez (Centro)'])
