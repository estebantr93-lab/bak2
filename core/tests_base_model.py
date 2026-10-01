"""BaseModel (created_at, updated_at, deleted_at) y traza de auditoría con valores anteriores y nuevos.

U2 · Clase 2: los campos de auditoría se centralizan en un modelo abstracto. Las fechas viven en cada
registro; quién hizo el cambio y qué valores cambió queda en colaboracion.AuditLog.
"""
import datetime
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from actividades.models import Activity, SocialCase
from agenda.models import Commitment, CommitmentFollowUp
from colaboracion.models import AuditLog
from core.models import ActivityType, BaseModel, Delegation, Parameter, Period, Position, TimeStampedModel
from core.testing import SesionTestMixin, sembrar_datos_demo
from evidencias.models import Evidence, Validation
from funcionarios.models import Employee
from medicion.models import Goal, Indicator, Weighting

HACE_UN_DIA = timezone.now() - datetime.timedelta(days=1)


def en(momento):
    """Fija la hora que usan auto_now y auto_now_add."""
    return mock.patch('django.utils.timezone.now', return_value=momento)


class ModelosBaseTests(TestCase):
    def test_entidades_operacionales_heredan_base_model_y_las_maestras_solo_las_fechas(self):
        for modelo in (Activity, SocialCase, Evidence, Validation, Commitment, CommitmentFollowUp):
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(issubclass(modelo, BaseModel))
        for modelo in (Delegation, Position, ActivityType, Period, Parameter, Employee, Goal, Weighting, Indicator):
            with self.subTest(modelo=modelo.__name__):
                self.assertTrue(issubclass(modelo, TimeStampedModel))
                self.assertFalse(issubclass(modelo, BaseModel))  # se desactivan con is_active, no se eliminan

    def test_los_modelos_base_son_abstractos(self):
        self.assertTrue(TimeStampedModel._meta.abstract)
        self.assertTrue(BaseModel._meta.abstract)


class FechasDeAuditoriaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def test_crear_fija_las_dos_fechas_y_modificar_solo_updated_at(self):
        with en(HACE_UN_DIA):
            delegacion = Delegation.objects.create(name='Delegación Sur', address='Calle 1')
        self.assertEqual(delegacion.created_at, HACE_UN_DIA)
        self.assertEqual(delegacion.updated_at, HACE_UN_DIA)
        delegacion.phone = '+56 51 200 0000'
        delegacion.save()
        delegacion.refresh_from_db()
        self.assertEqual(delegacion.created_at, HACE_UN_DIA)
        self.assertGreater(delegacion.updated_at, HACE_UN_DIA)

    def test_save_con_update_fields_tambien_actualiza_updated_at(self):
        actividad = Activity.objects.first()
        Activity.all_objects.filter(pk=actividad.pk).update(updated_at=HACE_UN_DIA)
        actividad.refresh_from_db()
        actividad.contact = 'Otro contacto'
        actividad.save(update_fields=['contact'])
        actividad.refresh_from_db()
        self.assertGreater(actividad.updated_at, HACE_UN_DIA)

    def test_borrado_logico_y_restauracion_actualizan_updated_at(self):
        compromiso = Commitment.objects.first()
        Commitment.all_objects.filter(pk=compromiso.pk).update(updated_at=HACE_UN_DIA)
        compromiso.refresh_from_db()
        compromiso.delete()
        compromiso.refresh_from_db()
        self.assertIsNotNone(compromiso.deleted_at)
        self.assertGreater(compromiso.updated_at, HACE_UN_DIA)
        Commitment.all_objects.filter(pk=compromiso.pk).update(updated_at=HACE_UN_DIA)
        compromiso.refresh_from_db()
        compromiso.restore()
        compromiso.refresh_from_db()
        self.assertIsNone(compromiso.deleted_at)
        self.assertGreater(compromiso.updated_at, HACE_UN_DIA)

    def test_seguimiento_actualiza_updated_at_del_compromiso(self):
        # El seguimiento cambia el estado del compromiso con QuerySet.update(), que no aplica auto_now.
        compromiso = Commitment.objects.exclude(status='done').first()
        Commitment.all_objects.filter(pk=compromiso.pk).update(updated_at=HACE_UN_DIA)
        CommitmentFollowUp.objects.create(commitment=compromiso, description='Avance en terreno', new_status='in_progress')
        compromiso.refresh_from_db()
        self.assertEqual(compromiso.status, 'in_progress')
        self.assertGreater(compromiso.updated_at, HACE_UN_DIA)


class TrazaConCambiosTests(SesionTestMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        sembrar_datos_demo()

    def datos_compromiso(self, **extra):
        datos = {
            'title': 'Reunión con junta de vecinos', 'description': '',
            'responsible': Employee.objects.get(name='Ana Pérez (Centro)').pk,
            'due_date': (timezone.localdate() + datetime.timedelta(days=10)).isoformat(),
            'status': 'pending', 'notes': '',
        }
        datos.update(extra)
        return datos

    def test_web_registra_quien_crea_y_quien_modifica_con_valor_anterior_y_nuevo(self):
        self.ingresar('admin_centro')
        self.client.post(reverse('compromiso_create'), self.datos_compromiso())
        compromiso = Commitment.objects.get(title='Reunión con junta de vecinos')
        creacion = AuditLog.objects.get(action='crear', entity_type='Commitment', entity_id=compromiso.pk)
        self.assertEqual(creacion.user.username, 'admin_centro')
        self.assertEqual(creacion.changes['title'], ['', 'Reunión con junta de vecinos'])

        self.client.post(reverse('compromiso_update', args=[compromiso.pk]),
                         self.datos_compromiso(title='Reunión con la junta de vecinos', status='in_progress'))
        cambio = AuditLog.objects.get(action='modificar', entity_type='Commitment', entity_id=compromiso.pk)
        self.assertEqual(cambio.user.username, 'admin_centro')
        self.assertEqual(cambio.changes['title'], ['Reunión con junta de vecinos', 'Reunión con la junta de vecinos'])
        self.assertEqual(cambio.changes['status'], ['Pendiente', 'En proceso'])  # etiquetas, no claves internas
        self.assertNotIn('due_date', cambio.changes)  # solo lo que cambió

    def test_guardar_sin_cambios_no_llena_la_traza(self):
        self.ingresar('admin_centro')
        self.client.post(reverse('compromiso_create'), self.datos_compromiso())
        compromiso = Commitment.objects.get(title='Reunión con junta de vecinos')
        self.client.post(reverse('compromiso_update', args=[compromiso.pk]), self.datos_compromiso())
        self.assertFalse(AuditLog.objects.filter(action='modificar', entity_id=compromiso.pk).exists())

    def _datos_del_admin(self, url):
        formulario = self.client.get(url).context['adminform'].form
        datos = {}
        for nombre, valor in formulario.initial.items():
            if nombre not in formulario.fields or valor is None:
                continue
            if isinstance(valor, bool):
                if valor:
                    datos[nombre] = 'on'
            else:
                datos[nombre] = getattr(valor, 'pk', valor)
        return datos

    def test_admin_registra_el_cambio_con_valor_anterior_y_nuevo(self):
        self.ingresar('admin_sgr')
        delegacion = Delegation.objects.get(name='Delegación Centro')
        url = reverse('admin:core_delegation_change', args=[delegacion.pk])
        datos = self._datos_del_admin(url)
        anterior = delegacion.address
        datos['address'] = 'Av. Francisco de Aguirre 300'
        self.client.post(url, datos)
        cambio = AuditLog.objects.get(action='modificar', entity_type='Delegation', entity_id=delegacion.pk)
        self.assertEqual(cambio.user.username, 'admin_sgr')
        self.assertEqual(cambio.changes, {'address': [anterior, 'Av. Francisco de Aguirre 300']})

    def test_admin_de_configuracion_guarda_los_valores(self):
        self.ingresar('admin_sgr')
        parametro = Parameter.objects.first()
        url = reverse('admin:core_parameter_change', args=[parametro.pk])
        datos = self._datos_del_admin(url)
        datos['value'] = '7'
        self.client.post(url, datos)
        cambio = AuditLog.objects.get(action='modificar_configuracion', entity_id=parametro.pk)
        self.assertEqual(cambio.changes['value'][1], '7')

    def test_la_ficha_del_admin_muestra_las_fechas_sin_permitir_editarlas(self):
        self.ingresar('admin_sgr')
        actividad = Activity.objects.filter(period__is_closed=False).first()
        respuesta = self.client.get(reverse('admin:actividades_activity_change', args=[actividad.pk]))
        solo_lectura = respuesta.context['adminform'].readonly_fields
        self.assertIn('created_at', solo_lectura)
        self.assertIn('updated_at', solo_lectura)
        self.assertNotIn('created_at', respuesta.context['adminform'].form.fields)
